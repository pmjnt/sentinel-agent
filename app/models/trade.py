from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.policy import PolicyViolation


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    side: TradeSide
    amount: Decimal = Field(gt=0)
    estimated_usd_value: Decimal = Field(gt=0)
    reason: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Trade symbol must not be empty.")
        return normalized


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    BLOCKED = "BLOCKED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    SAFE_TO_PROPOSE = "SAFE_TO_PROPOSE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class RebalancePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    violations: list[PolicyViolation] = Field(default_factory=list)
    actions: list[TradeAction] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    explanation: str
