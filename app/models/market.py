from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Volatility(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MarketData(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    price: Decimal = Field(gt=0)
    change_24h_percent: Decimal
    volatility: Volatility
    estimated_slippage_percent: Decimal = Field(ge=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Market symbol must not be empty.")
        return normalized


class MarketDataError(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    error: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Market symbol must not be empty.")
        return normalized


MarketDataResult = MarketData | MarketDataError
