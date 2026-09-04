from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.source import DataSource


class PortfolioAsset(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    amount: Decimal = Field(ge=0)
    usd_value: Decimal = Field(ge=0)
    weight: Decimal = Field(default=Decimal("0"), ge=0, le=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Asset symbol must not be empty.")
        return normalized


class Portfolio(BaseModel):
    model_config = ConfigDict(frozen=True)

    assets: list[PortfolioAsset]
    total_usd_value: Decimal = Field(ge=0)
    data_source: DataSource = DataSource.UNKNOWN
