from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PortfolioPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_stablecoin_weight: Decimal | None = Field(default=None, ge=0, le=1)
    max_asset_weight: Decimal | None = Field(default=None, ge=0, le=1)
    block_high_volatility: bool = False
    max_trade_usd_without_approval: Decimal | None = Field(default=None, ge=0)


class PolicyPatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_stablecoin_weight: Decimal | None = Field(default=None, ge=0, le=1)
    max_asset_weight: Decimal | None = Field(default=None, ge=0, le=1)
    block_high_volatility: bool | None = None
    max_trade_usd_without_approval: Decimal | None = Field(default=None, ge=0)


class ViolationType(str, Enum):
    MAX_ASSET_WEIGHT = "MAX_ASSET_WEIGHT"
    MIN_STABLECOIN_WEIGHT = "MIN_STABLECOIN_WEIGHT"


class ViolationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class PolicyViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: ViolationType
    asset: str | None = None
    current_value: Decimal = Field(ge=0)
    allowed_value: Decimal = Field(ge=0)
    severity: ViolationSeverity
    explanation: str

    @field_validator("asset")
    @classmethod
    def normalize_asset(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Violation asset must not be empty.")
        return normalized
