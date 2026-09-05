from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.analysis import PortfolioAnalysis
from app.models.policy import PortfolioPolicy
from app.models.profile import InvestorProfile


class ActivityKind(str, Enum):
    PORTFOLIO_READ = "PORTFOLIO_READ"
    MARKET_DATA_READ = "MARKET_DATA_READ"
    POLICY_UPDATE = "POLICY_UPDATE"
    POLICY_VIEW = "POLICY_VIEW"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    PROFILE_VIEW = "PROFILE_VIEW"
    RISK_EVALUATION = "RISK_EVALUATION"


class ActivityStatus(str, Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionStatus(str, Enum):
    NOT_EXECUTED = "NOT_EXECUTED"


class ActivityEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(gt=0)
    kind: ActivityKind
    status: ActivityStatus
    message: str


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(max_length=128)
    message: str = Field(max_length=8000)

    @field_validator("session_id", "message")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
        return normalized


class TextDeltaEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str


class StructuredSentinelResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    message: str
    policy: PortfolioPolicy
    profile: InvestorProfile
    analysis: PortfolioAnalysis | None = None
    activity: list[ActivityEvent] = Field(default_factory=list)
    ai_interpretation: str | None = None
    execution_status: ExecutionStatus = ExecutionStatus.NOT_EXECUTED
