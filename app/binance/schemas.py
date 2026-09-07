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
    # Binance's bulk endpoint includes inactive markets with an explicit zero.
    price: Decimal = Field(ge=0)

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


class ExchangeSymbolPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str
    status: str
    base_asset: str = Field(alias="baseAsset")
    quote_asset: str = Field(alias="quoteAsset")
    order_types: tuple[str, ...] = Field(alias="orderTypes")
    is_spot_trading_allowed: bool = Field(alias="isSpotTradingAllowed")
    quote_order_qty_market_allowed: bool = Field(
        alias="quoteOrderQtyMarketAllowed"
    )


class ExchangeInfoPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbols: list[ExchangeSymbolPayload]


class SpotOrderPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    symbol: str
    order_id: int = Field(alias="orderId")
    client_order_id: str = Field(alias="clientOrderId")
    status: str

    @field_validator("symbol", "client_order_id", "status")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Order field must not be empty.")
        return normalized
