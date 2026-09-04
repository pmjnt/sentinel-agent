from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpotBalancePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset: str
    free: Decimal = Field(ge=0)
    locked: Decimal = Field(ge=0)

    @field_validator("asset")
    @classmethod
    def normalize_asset(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Asset must not be empty.")
        return normalized


class SpotAccountPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    balances: list[SpotBalancePayload]


class PriceTickerPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    price: Decimal = Field(gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class Ticker24hPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str
    last_price: Decimal = Field(alias="lastPrice", gt=0)
    price_change_percent: Decimal = Field(alias="priceChangePercent")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class DepthPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bids: list[tuple[Decimal, Decimal]]
    asks: list[tuple[Decimal, Decimal]]
