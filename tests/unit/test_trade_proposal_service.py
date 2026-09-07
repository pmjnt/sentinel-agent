from decimal import Decimal

import pytest

from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.trade import TradeSide
from app.models.execution import ExecutionPlanStatus
from app.models.symbol import TradingSymbolInfo
from app.services.portfolio_service import calculate_portfolio
from app.services.trade_proposal_service import TradeProposalError, create_trade_plan


def _portfolio():
    return calculate_portfolio(
        [
            PortfolioAsset(symbol="BTC", amount="0.01", usd_value="1000"),
            PortfolioAsset(symbol="USDT", amount="500", usd_value="500"),
        ]
    )


def _market(slippage: str = "0.05", symbol: str = "BTCUSDT") -> MarketData:
    return MarketData(
        symbol=symbol,
        price="100000",
        change_24h_percent="1",
        volatility=Volatility.LOW,
        estimated_slippage_percent=slippage,
    )


def _symbol_info(symbol: str = "BTCUSDT") -> TradingSymbolInfo:
    return TradingSymbolInfo(
        symbol=symbol,
        status="TRADING",
        base_asset=symbol.removesuffix("USDT"),
        quote_asset="USDT",
        order_types=("MARKET",),
        is_spot_trading_allowed=True,
        quote_order_qty_market_allowed=True,
    )


def test_non_default_symbol_requires_separate_override_approval() -> None:
    plan = create_trade_plan(
        session_id="session-1",
        symbol="LINKUSDT",
        side=TradeSide.BUY,
        quote_usd=Decimal("50"),
        reason="Controlled LINK exposure.",
        policy=PortfolioPolicy(),
        portfolio=_portfolio(),
        market=_market(symbol="LINKUSDT"),
        symbol_info=_symbol_info("LINKUSDT"),
    )

    assert plan.requires_symbol_override is True
    assert plan.status is ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL


def test_creates_pending_plan_with_estimated_quantity() -> None:
    plan = create_trade_plan(
        session_id="session-1",
        symbol="BTCUSDT",
        side=TradeSide.BUY,
        quote_usd=Decimal("50"),
        reason="Controlled growth exposure.",
        policy=PortfolioPolicy(),
        portfolio=_portfolio(),
        market=_market(),
        symbol_info=_symbol_info(),
    )

    assert plan.quote_usd == Decimal("50")
    assert plan.estimated_quantity == Decimal("0.0005")


@pytest.mark.parametrize(
    ("symbol", "amount"),
    [("BTCUSDT", "9"), ("BTCUSDT", "101")],
)
def test_hard_limits_cannot_be_relaxed_by_policy(symbol: str, amount: str) -> None:
    with pytest.raises(TradeProposalError):
        create_trade_plan(
            session_id="session-1",
            symbol=symbol,
            side=TradeSide.BUY,
            quote_usd=Decimal(amount),
            reason="Test.",
            policy=PortfolioPolicy(max_trade_usd=Decimal("10000")),
            portfolio=_portfolio(),
            market=_market(symbol=symbol),
            symbol_info=_symbol_info(symbol),
        )


def test_policy_can_make_trade_limits_stricter() -> None:
    with pytest.raises(TradeProposalError, match="policy maximum"):
        create_trade_plan(
            session_id="session-1",
            symbol="BTCUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("50"),
            reason="Test.",
            policy=PortfolioPolicy(max_trade_usd=Decimal("25")),
            portfolio=_portfolio(),
            market=_market(),
            symbol_info=_symbol_info(),
        )


def test_buy_requires_sufficient_usdt_and_policy_slippage() -> None:
    with pytest.raises(TradeProposalError, match="slippage"):
        create_trade_plan(
            session_id="session-1",
            symbol="BTCUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("50"),
            reason="Test.",
            policy=PortfolioPolicy(max_slippage_percent=Decimal("0.01")),
            portfolio=_portfolio(),
            market=_market("0.05"),
            symbol_info=_symbol_info(),
        )


def test_high_volatility_policy_blocks_trade_proposal() -> None:
    market = _market()
    market = market.model_copy(update={"volatility": Volatility.HIGH})

    with pytest.raises(TradeProposalError, match="HIGH volatility"):
        create_trade_plan(
            session_id="session-1",
            symbol="BTCUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("50"),
            reason="Test.",
            policy=PortfolioPolicy(block_high_volatility=True),
            portfolio=_portfolio(),
            market=market,
            symbol_info=_symbol_info(),
        )


def test_projected_trade_cannot_create_portfolio_policy_violation() -> None:
    portfolio = calculate_portfolio(
        [
            PortfolioAsset(symbol="BTC", amount="0.004", usd_value="400"),
            PortfolioAsset(symbol="USDT", amount="600", usd_value="600"),
        ]
    )

    with pytest.raises(TradeProposalError, match="portfolio policy"):
        create_trade_plan(
            session_id="session-1",
            symbol="BTCUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("100"),
            reason="Test.",
            policy=PortfolioPolicy(max_asset_weight="0.45"),
            portfolio=portfolio,
            market=_market(),
            symbol_info=_symbol_info(),
        )


def test_trade_value_is_limited_to_currency_precision() -> None:
    with pytest.raises(TradeProposalError, match="two decimal"):
        create_trade_plan(
            session_id="session-1",
            symbol="BTCUSDT",
            side=TradeSide.BUY,
            quote_usd=Decimal("50.123"),
            reason="Test.",
            policy=PortfolioPolicy(),
            portfolio=_portfolio(),
            market=_market(),
            symbol_info=_symbol_info(),
        )
