from enum import Enum

from pydantic import BaseModel


class Volatility(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PortfolioAsset(BaseModel):
    symbol: str
    value_usd: float


class Portfolio(BaseModel):
    assets: list[PortfolioAsset]
    total_value_usd: float


class MarketData(BaseModel):
    symbol: str
    supported: bool
    price: float | None = None
    change_24h_percent: float | None = None
    volatility: Volatility | None = None
    error: str | None = None
