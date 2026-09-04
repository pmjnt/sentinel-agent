from decimal import Decimal

import pytest

from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy, ViolationType
from app.models.portfolio import Portfolio, PortfolioAsset
from app.models.trade import PlanStatus, TradeSide
from app.services.policy_service import find_policy_violations
from app.services.portfolio_service import calculate_portfolio
from app.services.rebalance_service import (
    MissingMarketDataError,
    build_rebalance_plan,
)


def _portfolio() -> Portfolio:
    return calculate_portfolio(
        [
            PortfolioAsset(
                symbol="BTC",
                amount=Decimal("0.05"),
                usd_value=Decimal("5500"),
            ),
            PortfolioAsset(
                symbol="ETH",
                amount=Decimal("0.58"),
                usd_value=Decimal("2500"),
            ),
            PortfolioAsset(
                symbol="USDT",
                amount=Decimal("2000"),
                usd_value=Decimal("2000"),
            ),
        ]
    )


def _btc_market() -> MarketData:
    return MarketData(
        symbol="BTCUSDT",
        price=Decimal("110000"),
        change_24h_percent=Decimal("-4.2"),
        volatility=Volatility.HIGH,
        estimated_slippage_percent=Decimal("0.05"),
    )


def test_builds_btc_sell_proposal_for_excess_weight() -> None:
    portfolio = _portfolio()
    violations = find_policy_violations(
        portfolio,
        PortfolioPolicy(
            min_stablecoin_weight=Decimal("0.30"),
            max_asset_weight=Decimal("0.40"),
        ),
    )

    plan = build_rebalance_plan(
        portfolio,
        violations,
        {"BTCUSDT": _btc_market()},
    )

    assert plan.status is PlanStatus.DRAFT
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.symbol == "BTCUSDT"
    assert action.side is TradeSide.SELL
    assert action.estimated_usd_value == Decimal("1500.00")
    assert action.amount == Decimal("0.01363636")


def test_stablecoin_shortfall_alone_does_not_invent_a_funding_trade() -> None:
    portfolio = _portfolio()
    violations = find_policy_violations(
        portfolio,
        PortfolioPolicy(min_stablecoin_weight=Decimal("0.30")),
    )

    assert [violation.type for violation in violations] == [
        ViolationType.MIN_STABLECOIN_WEIGHT
    ]
    plan = build_rebalance_plan(portfolio, violations, {})
    assert plan.actions == []


def test_missing_market_data_stops_proposal_calculation() -> None:
    portfolio = _portfolio()
    violations = find_policy_violations(
        portfolio,
        PortfolioPolicy(max_asset_weight=Decimal("0.40")),
    )

    with pytest.raises(MissingMarketDataError, match="BTCUSDT"):
        build_rebalance_plan(portfolio, violations, {})
