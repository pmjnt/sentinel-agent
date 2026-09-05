from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvestmentObjective(str, Enum):
    CAPITAL_PRESERVATION = "CAPITAL_PRESERVATION"
    BALANCED = "BALANCED"
    GROWTH = "GROWTH"


class RiskTolerance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class LiquidityNeed(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class InvestorProfileField(str, Enum):
    OBJECTIVE = "objective"
    TIME_HORIZON_MONTHS = "time_horizon_months"
    RISK_TOLERANCE = "risk_tolerance"
    ACCEPTABLE_LOSS_PERCENT = "acceptable_loss_percent"
    LIQUIDITY_NEED = "liquidity_need"
    EXCLUDED_ASSETS = "excluded_assets"


class InvestorProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    objective: InvestmentObjective | None = None
    time_horizon_months: int | None = Field(default=None, gt=0, le=1200)
    risk_tolerance: RiskTolerance | None = None
    acceptable_loss_percent: Decimal | None = Field(default=None, ge=0, le=100)
    liquidity_need: LiquidityNeed | None = None
    excluded_assets: list[str] = Field(default_factory=list)

    @field_validator("excluded_assets")
    @classmethod
    def normalize_assets(cls, values: list[str]) -> list[str]:
        normalized: dict[str, None] = {}
        for value in values:
            symbol = value.strip().upper()
            if not symbol:
                raise ValueError("Excluded asset symbols must not be empty.")
            normalized[symbol] = None
        return list(normalized)


class InvestorProfilePatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    objective: InvestmentObjective | None = None
    time_horizon_months: int | None = Field(default=None, gt=0, le=1200)
    risk_tolerance: RiskTolerance | None = None
    acceptable_loss_percent: Decimal | None = Field(default=None, ge=0, le=100)
    liquidity_need: LiquidityNeed | None = None
    excluded_assets: list[str] | None = None

    @field_validator("excluded_assets")
    @classmethod
    def normalize_assets(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return InvestorProfile.normalize_assets(values)
