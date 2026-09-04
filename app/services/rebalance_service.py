from decimal import Decimal, ROUND_HALF_UP

from app.models.market import MarketData
from app.models.policy import PolicyViolation, ViolationType
from app.models.portfolio import Portfolio
from app.models.trade import RebalancePlan, TradeAction, TradeSide


USD_PRECISION = Decimal("0.01")
ASSET_PRECISION = Decimal("0.00000001")


class MissingMarketDataError(ValueError):
    """Raised when a proposal cannot be priced without inventing market data."""


def build_rebalance_plan(
    portfolio: Portfolio,
    violations: list[PolicyViolation],
    market_data: dict[str, MarketData],
) -> RebalancePlan:
    """Build draft sell actions for assets above their configured maximum."""
    normalized_market = {
        symbol.strip().upper(): data for symbol, data in market_data.items()
    }
    actions = [
        _build_excess_asset_action(portfolio, violation, normalized_market)
        for violation in violations
        if violation.type is ViolationType.MAX_ASSET_WEIGHT
    ]

    explanation = (
        "Reduce assets that exceed the configured maximum allocation."
        if actions
        else "No deterministic rebalance action can be built from these violations."
    )
    return RebalancePlan(
        violations=violations,
        actions=actions,
        explanation=explanation,
    )


def _build_excess_asset_action(
    portfolio: Portfolio,
    violation: PolicyViolation,
    market_data: dict[str, MarketData],
) -> TradeAction:
    if violation.asset is None:
        raise ValueError("Maximum asset violation must identify an asset.")

    market_symbol = f"{violation.asset}USDT"
    market = market_data.get(market_symbol)
    if market is None:
        raise MissingMarketDataError(
            f"Market data is required for {market_symbol}."
        )

    excess_weight = violation.current_value - violation.allowed_value
    excess_usd = (excess_weight * portfolio.total_usd_value).quantize(
        USD_PRECISION,
        rounding=ROUND_HALF_UP,
    )
    amount = (excess_usd / market.price).quantize(
        ASSET_PRECISION,
        rounding=ROUND_HALF_UP,
    )
    return TradeAction(
        symbol=market_symbol,
        side=TradeSide.SELL,
        amount=amount,
        estimated_usd_value=excess_usd,
        reason=(
            f"{violation.asset} exceeds the configured maximum portfolio weight."
        ),
    )
