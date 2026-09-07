import asyncio
from decimal import Decimal

import pytest

from app.execution.store import InMemoryExecutionPlanStore, PlanStateError
from app.models.execution import ExecutionPlanStatus, OrderExecutionResult
from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.symbol import TradingSymbolInfo
from app.models.trade import TradeSide
from app.services.execution_service import DemoExecutionService, ExecutionBlockedError
from app.services.portfolio_service import calculate_portfolio
from app.services.trade_proposal_service import create_trade_plan


class FakeGateway:
    def __init__(self) -> None:
        self.submissions = 0
        self.portfolio_reads = 0
        self.market = MarketData(
            symbol="BTCUSDT",
            price="100000",
            change_24h_percent="1",
            volatility=Volatility.LOW,
            estimated_slippage_percent="0.05",
        )
        self.symbol_info = TradingSymbolInfo(
            symbol="BTCUSDT",
            status="TRADING",
            base_asset="BTC",
            quote_asset="USDT",
            order_types=("MARKET",),
            is_spot_trading_allowed=True,
            quote_order_qty_market_allowed=True,
        )

    async def get_portfolio(self):
        self.portfolio_reads += 1
        return calculate_portfolio(
            [
                PortfolioAsset(symbol="BTC", amount="0.01", usd_value="1000"),
                PortfolioAsset(symbol="USDT", amount="500", usd_value="500"),
            ]
        )

    async def get_market_data(self, symbol):
        return self.market

    async def get_symbol_info(self, symbol):
        return self.symbol_info

    async def submit_market_order(self, **kwargs):
        self.submissions += 1
        return OrderExecutionResult(
            order_id=42,
            client_order_id=kwargs["client_order_id"],
            symbol=kwargs["symbol"],
            status="FILLED",
        )

    async def get_order(self, symbol, client_order_id):
        return OrderExecutionResult(
            order_id=42,
            client_order_id=client_order_id,
            symbol=symbol,
            status="FILLED",
        )


def _setup(policy: PortfolioPolicy | None = None):
    gateway = FakeGateway()
    store = InMemoryExecutionPlanStore()
    portfolio = asyncio.run(gateway.get_portfolio())
    plan = create_trade_plan(
        session_id="session-1",
        symbol="BTCUSDT",
        side=TradeSide.BUY,
        quote_usd=Decimal("50"),
        reason="Controlled growth exposure.",
        policy=policy or PortfolioPolicy(),
        portfolio=portfolio,
        market=gateway.market,
        symbol_info=gateway.symbol_info,
    )
    store.create(plan)
    service = DemoExecutionService(
        gateway=gateway,
        plans=store,
        policy_loader=lambda _session_id: policy or PortfolioPolicy(),
        enabled=True,
    )
    return gateway, store, service, plan


def test_approval_revalidates_executes_verifies_and_refreshes() -> None:
    gateway, _store, service, plan = _setup()

    executed = asyncio.run(service.approve_and_execute("session-1", plan.plan_id))

    assert executed.status is ExecutionPlanStatus.EXECUTED
    assert executed.order_id == 42
    assert gateway.submissions == 1
    assert gateway.portfolio_reads == 3  # initial proposal, revalidation, refresh


def test_duplicate_approval_never_submits_second_order() -> None:
    gateway, _store, service, plan = _setup()
    first = asyncio.run(service.approve_and_execute("session-1", plan.plan_id))

    second = asyncio.run(service.approve_and_execute("session-1", plan.plan_id))

    assert second == first
    assert gateway.submissions == 1


def test_execution_is_disabled_unless_explicitly_enabled() -> None:
    _gateway, store, _service, plan = _setup()
    disabled = DemoExecutionService(
        gateway=FakeGateway(),
        plans=store,
        policy_loader=lambda _session_id: PortfolioPolicy(),
        enabled=False,
    )

    with pytest.raises(ExecutionBlockedError, match="disabled"):
        asyncio.run(disabled.approve_and_execute("session-1", plan.plan_id))


def test_changed_policy_blocks_before_order_submission() -> None:
    gateway, store, _service, plan = _setup()
    service = DemoExecutionService(
        gateway=gateway,
        plans=store,
        policy_loader=lambda _session_id: PortfolioPolicy(max_trade_usd="25"),
        enabled=True,
    )

    with pytest.raises(ExecutionBlockedError, match="policy maximum"):
        asyncio.run(service.approve_and_execute("session-1", plan.plan_id))

    assert gateway.submissions == 0
    assert store.get("session-1", plan.plan_id).status is ExecutionPlanStatus.FAILED


def test_symbol_becoming_inactive_blocks_before_order_submission() -> None:
    gateway, store, service, plan = _setup()
    gateway.symbol_info = gateway.symbol_info.model_copy(update={"status": "BREAK"})

    with pytest.raises(ExecutionBlockedError, match="not currently trading"):
        asyncio.run(service.approve_and_execute("session-1", plan.plan_id))

    assert gateway.submissions == 0
    assert store.get("session-1", plan.plan_id).status is ExecutionPlanStatus.FAILED


def test_reject_closes_pending_plan_without_submission() -> None:
    gateway, _store, service, plan = _setup()

    rejected = service.reject("session-1", plan.plan_id)

    assert rejected.status is ExecutionPlanStatus.REJECTED
    assert gateway.submissions == 0
