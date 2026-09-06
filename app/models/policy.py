from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PortfolioPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_stablecoin_weight: Decimal | None = Field(default=None, ge=0, le=1)
    max_asset_weight: Decimal | None = Field(default=None, ge=0, le=1)
    block_high_volatility: bool = False
    max_trade_usd_without_approval: Decimal | None = Field(default=None, ge=0)
    max_trade_usd: Decimal | None = Field(default=None, ge=0)
    max_slippage_percent: Decimal | None = Field(default=None, ge=0, le=100)
    allowed_trade_symbols: tuple[str, ...] | None = None

    @field_validator("allowed_trade_symbols")
    @classmethod
    def normalize_allowed_symbols(
        cls, value: tuple[str, ...] | None
    ) -> tuple[str, ...] | None:
        if value is None:
            return None
        normalized = tuple(dict.fromkeys(symbol.strip().upper() for symbol in value))
        if not normalized or any(not symbol for symbol in normalized):
            raise ValueError("Allowed trade symbols must not be empty.")
        return normalized


class PolicyPatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_stablecoin_weight: Decimal | None = Field(default=None, ge=0, le=1)
    max_asset_weight: Decimal | None = Field(default=None, ge=0, le=1)
    block_high_volatility: bool | None = None
    max_trade_usd_without_approval: Decimal | None = Field(default=None, ge=0)
    max_trade_usd: Decimal | None = Field(default=None, ge=0)
    max_slippage_percent: Decimal | None = Field(default=None, ge=0, le=100)
    allowed_trade_symbols: tuple[str, ...] | None = None

    @field_validator("allowed_trade_symbols")
    @classmethod
    def normalize_allowed_symbols(
        cls, value: tuple[str, ...] | None
    ) -> tuple[str, ...] | None:
        return PortfolioPolicy.normalize_allowed_symbols(value)


class PolicyField(str, Enum):
    MIN_STABLECOIN_WEIGHT = "min_stablecoin_weight"
    MAX_ASSET_WEIGHT = "max_asset_weight"
    BLOCK_HIGH_VOLATILITY = "block_high_volatility"
    MAX_TRADE_USD_WITHOUT_APPROVAL = "max_trade_usd_without_approval"
    MAX_TRADE_USD = "max_trade_usd"
    MAX_SLIPPAGE_PERCENT = "max_slippage_percent"
    ALLOWED_TRADE_SYMBOLS = "allowed_trade_symbols"


class PolicyChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    field: PolicyField
    value: Decimal | bool | str | tuple[str, ...] | None


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
