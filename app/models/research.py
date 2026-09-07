from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResearchTimeframe(str, Enum):
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class ResearchPriority(str, Enum):
    LIQUIDITY = "LIQUIDITY"
    MOMENTUM = "MOMENTUM"
    DOWNSIDE_CONTROL = "DOWNSIDE_CONTROL"
    VOLATILITY_OPPORTUNITY = "VOLATILITY_OPPORTUNITY"


class TrendDirection(str, Enum):
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


_BARS_PER_DAY = {
    ResearchTimeframe.M15: 96,
    ResearchTimeframe.H1: 24,
    ResearchTimeframe.H4: 6,
    ResearchTimeframe.D1: 1,
}


class MarketResearchPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_limit: int = Field(ge=3, le=10)
    timeframes: tuple[ResearchTimeframe, ...] = Field(min_length=1, max_length=2)
    lookback_days: int = Field(ge=1, le=90)
    priorities: tuple[ResearchPriority, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_unique_bounded_research(self) -> "MarketResearchPlan":
        if len(set(self.timeframes)) != len(self.timeframes):
            raise ValueError("Research timeframes must be unique.")
        if len(set(self.priorities)) != len(self.priorities):
            raise ValueError("Research priorities must be unique.")
        for timeframe in self.timeframes:
            bars = self.lookback_days * _BARS_PER_DAY[timeframe]
            if bars < 20:
                raise ValueError("Each research timeframe requires at least 20 candles.")
            if bars > 1000:
                raise ValueError("A research timeframe cannot exceed 1,000 candles.")
        return self


class MarketTicker(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    price: Decimal = Field(gt=0)
    change_24h_percent: Decimal
    quote_volume: Decimal = Field(ge=0)
    observed_at: datetime

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Market symbol must not be empty.")
        return normalized


class MarketScan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidates: tuple[MarketTicker, ...]
    observed_at: datetime


class MarketCandle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    open_time: datetime
    close_time: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    quote_volume: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_candle(self) -> "MarketCandle":
        if self.close_time <= self.open_time:
            raise ValueError("Candle close time must follow open time.")
        if self.high < max(self.open, self.close) or self.low > min(
            self.open, self.close
        ):
            raise ValueError("Candle OHLC values are inconsistent.")
        return self


class TimeframeResearch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timeframe: ResearchTimeframe
    sample_size: int = Field(ge=2)
    return_percent: Decimal
    trend: TrendDirection
    realized_volatility_percent: Decimal = Field(ge=0)
    max_drawdown_percent: Decimal = Field(ge=0)
    volume_change_percent: Decimal


class CandidateResearch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: MarketTicker
    timeframes: tuple[TimeframeResearch, ...]


class MarketResearchResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    plan: MarketResearchPlan
    scan: MarketScan
    analyzed_candidates: tuple[CandidateResearch, ...]
    failed_symbols: tuple[str, ...] = ()
