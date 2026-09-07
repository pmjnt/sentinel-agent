from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.trade import TradeSide


class ExecutionPlanStatus(str, Enum):
    PENDING_SYMBOL_APPROVAL = "PENDING_SYMBOL_APPROVAL"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    session_id: str
    symbol: str
    side: TradeSide
    quote_usd: Decimal = Field(gt=0)
    estimated_quantity: Decimal = Field(gt=0)
    estimated_price: Decimal = Field(gt=0)
    reason: str
    created_at: datetime
    expires_at: datetime
    status: ExecutionPlanStatus = ExecutionPlanStatus.PENDING_APPROVAL
    order_id: int | None = None
    order_status: str | None = None
    failure_reason: str | None = None
    requires_symbol_override: bool = False

    @field_validator("plan_id", "session_id", "reason")
    @classmethod
    def required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be empty.")
        return normalized

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Symbol must not be empty.")
        return normalized


class OrderExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: int
    client_order_id: str
    symbol: str
    status: str
