from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RiskStatus(str, Enum):
    BLOCKED = "BLOCKED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    SAFE_TO_PROPOSE = "SAFE_TO_PROPOSE"


class RiskReasonCode(str, Enum):
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    APPROVAL_THRESHOLD_EXCEEDED = "APPROVAL_THRESHOLD_EXCEEDED"
    NO_RESTRICTION_TRIGGERED = "NO_RESTRICTION_TRIGGERED"


class RiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: RiskStatus
    reason_codes: list[RiskReasonCode] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
