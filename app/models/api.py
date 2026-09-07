from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.analysis import PortfolioAnalysis
from app.models.execution import ExecutionPlan
from app.models.policy import PortfolioPolicy
from app.models.profile import InvestorProfile
from app.models.research import MarketResearchResult


class ActivityKind(str, Enum):
    PORTFOLIO_READ = "PORTFOLIO_READ"
    MARKET_DATA_READ = "MARKET_DATA_READ"
    POLICY_UPDATE = "POLICY_UPDATE"
    POLICY_VIEW = "POLICY_VIEW"
    PROFILE_UPDATE = "PROFILE_UPDATE"
    PROFILE_VIEW = "PROFILE_VIEW"
    RISK_EVALUATION = "RISK_EVALUATION"
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    RESEARCH_PLAN = "RESEARCH_PLAN"
    MARKET_SCAN = "MARKET_SCAN"
    MARKET_HISTORY = "MARKET_HISTORY"
    MARKET_RESEARCH = "MARKET_RESEARCH"


class ActivityStatus(str, Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionStatus(str, Enum):
    NOT_EXECUTED = "NOT_EXECUTED"
    PENDING_SYMBOL_APPROVAL = "PENDING_SYMBOL_APPROVAL"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


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
    provider: str = Field(max_length=32)
    model: str = Field(max_length=200)

    @field_validator("session_id", "message", "provider", "model")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
        return normalized

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.lower()


class ModelOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    model: str
    label: str


class ModelCatalogResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    default: ModelOption
    models: list[ModelOption]


class TextDeltaEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str


class StructuredSentinelResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    provider: str | None = None
    model: str | None = None
    message: str
    policy: PortfolioPolicy
    profile: InvestorProfile
    analysis: PortfolioAnalysis | None = None
    activity: list[ActivityEvent] = Field(default_factory=list)
    ai_interpretation: str | None = None
    execution_status: ExecutionStatus = ExecutionStatus.NOT_EXECUTED
    execution_plan: ExecutionPlan | None = None
    market_research: MarketResearchResult | None = None


class PlanActionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(max_length=128)

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session ID must not be empty.")
        return normalized
