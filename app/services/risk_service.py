from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.risk import RiskDecision, RiskReasonCode, RiskStatus
from app.models.trade import RebalancePlan


class MissingRiskMarketDataError(ValueError):
    """Raised when a volatility rule cannot be evaluated safely."""


def evaluate_rebalance_risk(
    policy: PortfolioPolicy,
    plan: RebalancePlan,
    market_data: dict[str, MarketData],
) -> RiskDecision:
    """Apply blocking rules before approval and safe-proposal rules."""
    normalized_market = {
        symbol.strip().upper(): data for symbol, data in market_data.items()
    }

    if policy.block_high_volatility:
        high_volatility_symbols = _find_high_volatility_symbols(
            plan,
            normalized_market,
        )
        if high_volatility_symbols:
            symbols = ", ".join(high_volatility_symbols)
            return RiskDecision(
                status=RiskStatus.BLOCKED,
                reason_codes=[RiskReasonCode.HIGH_VOLATILITY],
                reasons=[f"High volatility blocks rebalancing for {symbols}."],
            )

    threshold = policy.max_trade_usd_without_approval
    if threshold is not None:
        actions_over_threshold = [
            action
            for action in plan.actions
            if action.estimated_usd_value > threshold
        ]
        if actions_over_threshold:
            symbols = ", ".join(action.symbol for action in actions_over_threshold)
            return RiskDecision(
                status=RiskStatus.REQUIRES_APPROVAL,
                reason_codes=[RiskReasonCode.APPROVAL_THRESHOLD_EXCEEDED],
                reasons=[
                    f"The proposed value for {symbols} exceeds the approval threshold."
                ],
            )

    return RiskDecision(
        status=RiskStatus.SAFE_TO_PROPOSE,
        reason_codes=[RiskReasonCode.NO_RESTRICTION_TRIGGERED],
        reasons=["No configured blocking or approval rule was triggered."],
    )


def _find_high_volatility_symbols(
    plan: RebalancePlan,
    market_data: dict[str, MarketData],
) -> list[str]:
    high_volatility_symbols: list[str] = []
    for action in plan.actions:
        market = market_data.get(action.symbol)
        if market is None:
            raise MissingRiskMarketDataError(
                f"Market data is required to evaluate {action.symbol}."
            )
        if market.volatility is Volatility.HIGH:
            high_volatility_symbols.append(action.symbol)
    return high_volatility_symbols
