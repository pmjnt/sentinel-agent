from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, field_validator


class TradingSymbolInfo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    order_types: tuple[str, ...]
    is_spot_trading_allowed: bool
    quote_order_qty_market_allowed: bool

    @field_validator("symbol", "status", "base_asset", "quote_asset")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Symbol information must not contain empty text.")
        return normalized


class TradingSymbolInfoError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    error: str


TradingSymbolInfoResult: TypeAlias = TradingSymbolInfo | TradingSymbolInfoError
