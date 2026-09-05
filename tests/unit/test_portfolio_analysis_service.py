import asyncio
from decimal import Decimal

import pytest

from app.models.market import MarketData, MarketDataError, Volatility
from app.models.policy import PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.risk import RiskStatus
from app.models.trade import PlanStatus, TradeSide
from app.services.portfolio_analysis_service import (
    AnalysisDataError,
    PortfolioAnalysisService,
    evaluate_portfolio_observations,
    required_market_symbols,
)
from app.services.portfolio_service import calculate_portfolio


class FakeGateway:
    def __init__(
        self,
        market_results: dict[str, MarketData | MarketDataError] | None = None,
    ) -> None:
        self.market_results = market_results or {}
        self.market_requests: list[str] = []

    async def get_portfolio(self):
        return calculate_portfolio(
            [
                PortfolioAsset(
                    symbol="BTC",
                    amount=Decimal("0.05"),
                    usd_value=Decimal("5500"),
                ),
                PortfolioAsset(
                    symbol="ETH",
                    amount=Decimal("0.8"),
                    usd_value=Decimal("2500"),
                ),
                PortfolioAsset(
                    symbol="USDT",
                    amount=Decimal("2000"),
                    usd_value=Decimal("2000"),
                ),
            ]
        )

    async def get_market_data(self, symbol: str):
        self.market_requests.append(symbol)
        return self.market_results[symbol]


def _market(
    symbol: str = "BTCUSDT",
    volatility: Volatility = Volatility.HIGH,
) -> MarketData:
    return MarketData(
        symbol=symbol,
        price=Decimal("110000"),
        change_24h_percent=Decimal("-4.2"),
        volatility=volatility,
        estimated_slippage_percent=Decimal("0.05"),
    )


def _portfolio():
    return calculate_portfolio(
        [
            PortfolioAsset(
                symbol="BTC",
                amount=Decimal("0.05"),
                usd_value=Decimal("5500"),
            ),
            PortfolioAsset(
                symbol="ETH",
                amount=Decimal("0.8"),
                usd_value=Decimal("2500"),
            ),
            PortfolioAsset(
                symbol="USDT",
                amount=Decimal("2000"),
                usd_value=Decimal("2000"),
            ),
        ]
    )


def test_required_market_symbols_uses_focus_and_policy_violations() -> None:
    symbols = required_market_symbols(
        _portfolio(),
        PortfolioPolicy(max_asset_weight=Decimal("0.40")),
        ["BTC", "ETH"],
    )

    assert symbols == ["BTCUSDT", "ETHUSDT"]


def test_observation_evaluation_rejects_missing_required_market() -> None:
    with pytest.raises(
        AnalysisDataError,
        match="Required market data could not be verified",
    ):
        evaluate_portfolio_observations(
            PortfolioPolicy(max_asset_weight=Decimal("0.40")),
            _portfolio(),
            {},
        )


def test_observation_evaluation_reaches_blocked_without_gateway() -> None:
    result = evaluate_portfolio_observations(
        PortfolioPolicy(
            min_stablecoin_weight=Decimal("0.30"),
            max_asset_weight=Decimal("0.40"),
            block_high_volatility=True,
            max_trade_usd_without_approval=Decimal("1000"),
        ),
        _portfolio(),
        {"BTCUSDT": _market()},
    )

    assert len(result.violations) == 2
    assert result.plan.actions[0].estimated_usd_value == Decimal("1500.00")
    assert result.risk_decision.status is RiskStatus.BLOCKED


def test_builds_and_blocks_a_btc_rebalance_deterministically() -> None:
    gateway = FakeGateway({"BTCUSDT": _market()})
    service = PortfolioAnalysisService(gateway)
    policy = PortfolioPolicy(
        min_stablecoin_weight=Decimal("0.30"),
        max_asset_weight=Decimal("0.40"),
        block_high_volatility=True,
        max_trade_usd_without_approval=Decimal("1000"),
    )

    result = asyncio.run(service.analyze(policy, []))

    assert gateway.market_requests == ["BTCUSDT"]
    assert len(result.violations) == 2
    assert len(result.plan.actions) == 1
    action = result.plan.actions[0]
    assert action.side is TradeSide.SELL
    assert action.estimated_usd_value == Decimal("1500.00")
    assert result.risk_decision.status is RiskStatus.BLOCKED
    assert result.plan.status is PlanStatus.BLOCKED


def test_focus_symbol_requests_market_without_concentration_policy() -> None:
    gateway = FakeGateway({"BTCUSDT": _market()})

    result = asyncio.run(
        PortfolioAnalysisService(gateway).analyze(
            PortfolioPolicy(),
            ["BTC"],
        )
    )

    assert gateway.market_requests == ["BTCUSDT"]
    assert [market.symbol for market in result.market_data] == ["BTCUSDT"]


def test_duplicate_focus_and_violation_request_market_once() -> None:
    gateway = FakeGateway({"BTCUSDT": _market()})

    asyncio.run(
        PortfolioAnalysisService(gateway).analyze(
            PortfolioPolicy(max_asset_weight=Decimal("0.40")),
            ["BTC", "BTCUSDT"],
        )
    )

    assert gateway.market_requests == ["BTCUSDT"]


def test_stablecoin_focus_does_not_invent_stablecoin_pair() -> None:
    gateway = FakeGateway()

    result = asyncio.run(
        PortfolioAnalysisService(gateway).analyze(
            PortfolioPolicy(),
            ["USDT"],
        )
    )

    assert gateway.market_requests == []
    assert result.market_data == []


def test_market_error_fails_closed_with_sanitized_error() -> None:
    gateway = FakeGateway(
        {
            "BTCUSDT": MarketDataError(
                symbol="BTCUSDT",
                error="secret CLI details",
            )
        }
    )

    with pytest.raises(
        AnalysisDataError,
        match="Required market data could not be verified",
    ) as error:
        asyncio.run(
            PortfolioAnalysisService(gateway).analyze(
                PortfolioPolicy(),
                ["BTC"],
            )
        )

    assert "secret CLI details" not in str(error.value)


def test_raised_market_gateway_error_is_also_sanitized() -> None:
    class RaisingMarketGateway(FakeGateway):
        async def get_market_data(self, symbol: str):
            raise RuntimeError("private subprocess diagnostic")

    with pytest.raises(
        AnalysisDataError,
        match="Required market data could not be verified",
    ) as error:
        asyncio.run(
            PortfolioAnalysisService(RaisingMarketGateway()).analyze(
                PortfolioPolicy(),
                ["BTC"],
            )
        )

    assert "private subprocess diagnostic" not in str(error.value)


def test_market_cancellation_is_propagated_not_treated_as_success() -> None:
    class CancelledMarketGateway(FakeGateway):
        async def get_market_data(self, symbol: str):
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            PortfolioAnalysisService(CancelledMarketGateway()).analyze(
                PortfolioPolicy(),
                ["BTC"],
            )
        )
