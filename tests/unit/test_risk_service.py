from decimal import Decimal

from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.risk import RiskReasonCode, RiskStatus
from app.models.trade import RebalancePlan, TradeAction, TradeSide
from app.services.risk_service import evaluate_rebalance_risk


def _plan(usd_value: str) -> RebalancePlan:
    return RebalancePlan(
        actions=[
            TradeAction(
                symbol="BTCUSDT",
                side=TradeSide.SELL,
                amount=Decimal("0.01"),
                estimated_usd_value=Decimal(usd_value),
                reason="BTC exceeds its maximum allocation.",
            )
        ],
        explanation="Reduce BTC concentration.",
    )


def _market(volatility: Volatility) -> dict[str, MarketData]:
    return {
        "BTCUSDT": MarketData(
            symbol="BTCUSDT",
            price=Decimal("110000"),
            change_24h_percent=Decimal("-4.2"),
            volatility=volatility,
            estimated_slippage_percent=Decimal("0.05"),
        )
    }


def test_high_volatility_blocks_trade() -> None:
    decision = evaluate_rebalance_risk(
        PortfolioPolicy(block_high_volatility=True),
        _plan("500"),
        _market(Volatility.HIGH),
    )

    assert decision.status is RiskStatus.BLOCKED
    assert decision.reason_codes == [RiskReasonCode.HIGH_VOLATILITY]


def test_medium_volatility_does_not_block() -> None:
    decision = evaluate_rebalance_risk(
        PortfolioPolicy(
            block_high_volatility=True,
            max_trade_usd_without_approval=Decimal("1000"),
        ),
        _plan("500"),
        _market(Volatility.MEDIUM),
    )

    assert decision.status is RiskStatus.SAFE_TO_PROPOSE


def test_trade_over_threshold_requires_approval() -> None:
    decision = evaluate_rebalance_risk(
        PortfolioPolicy(max_trade_usd_without_approval=Decimal("1000")),
        _plan("1500"),
        _market(Volatility.MEDIUM),
    )

    assert decision.status is RiskStatus.REQUIRES_APPROVAL
    assert decision.reason_codes == [
        RiskReasonCode.APPROVAL_THRESHOLD_EXCEEDED
    ]


def test_blocking_condition_has_priority_over_approval() -> None:
    decision = evaluate_rebalance_risk(
        PortfolioPolicy(
            block_high_volatility=True,
            max_trade_usd_without_approval=Decimal("1000"),
        ),
        _plan("1500"),
        _market(Volatility.HIGH),
    )

    assert decision.status is RiskStatus.BLOCKED
    assert decision.reason_codes == [RiskReasonCode.HIGH_VOLATILITY]


def test_safe_plan_returns_safe_to_propose() -> None:
    decision = evaluate_rebalance_risk(
        PortfolioPolicy(max_trade_usd_without_approval=Decimal("1000")),
        _plan("500"),
        _market(Volatility.LOW),
    )

    assert decision.status is RiskStatus.SAFE_TO_PROPOSE
    assert decision.reason_codes == [RiskReasonCode.NO_RESTRICTION_TRIGGERED]
