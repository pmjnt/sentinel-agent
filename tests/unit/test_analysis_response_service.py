from decimal import Decimal

from app.models.analysis import PortfolioAnalysis
from app.models.market import MarketData, Volatility
from app.models.policy import PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.risk import RiskDecision, RiskReasonCode, RiskStatus
from app.models.trade import PlanStatus, RebalancePlan
from app.services.analysis_response_service import format_authoritative_analysis


def test_tiny_slippage_is_rendered_as_nearly_zero_not_scientific_notation() -> None:
    policy = PortfolioPolicy()
    analysis = PortfolioAnalysis(
        policy=policy,
        portfolio=Portfolio(assets=[], total_usd_value=Decimal("0")),
        violations=[],
        market_data=[
            MarketData(
                symbol="USDCUSDT",
                price=Decimal("0.9999"),
                change_24h_percent=Decimal("0.015"),
                volatility=Volatility.LOW,
                estimated_slippage_percent=Decimal(
                    "4.000560078410977536855159722E-26"
                ),
            )
        ],
        plan=RebalancePlan(
            violations=[],
            actions=[],
            status=PlanStatus.SAFE_TO_PROPOSE,
            explanation="No action required.",
        ),
        risk_decision=RiskDecision(
            status=RiskStatus.SAFE_TO_PROPOSE,
            reason_codes=[RiskReasonCode.NO_RESTRICTION_TRIGGERED],
            reasons=["No restriction triggered."],
        ),
    )

    rendered = format_authoritative_analysis(analysis)

    assert "estimated slippage ~0.0000%" in rendered
    assert "E-26" not in rendered
