from pydantic import BaseModel, ConfigDict

from app.models.market import MarketData
from app.models.policy import PolicyViolation, PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.risk import RiskDecision
from app.models.trade import RebalancePlan


class PortfolioAnalysis(BaseModel):
    """Validated facts and deterministic decisions for one analysis request."""

    model_config = ConfigDict(frozen=True)

    policy: PortfolioPolicy
    portfolio: Portfolio
    violations: list[PolicyViolation]
    market_data: list[MarketData]
    plan: RebalancePlan
    risk_decision: RiskDecision
