from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.research import (
    MarketCandle,
    MarketResearchPlan,
    MarketTicker,
    ResearchPriority,
    ResearchTimeframe,
    TrendDirection,
)
from app.services.market_research_service import (
    analyze_candles,
    candle_limit,
    rank_market_candidates,
)


def _ticker(symbol: str, quote_volume: str) -> MarketTicker:
    return MarketTicker(
        symbol=symbol,
        price="100",
        change_24h_percent="1",
        quote_volume=quote_volume,
        observed_at=datetime(2026, 9, 7, tzinfo=UTC),
    )


def _candles(closes: list[str], volumes: list[str] | None = None):
    start = datetime(2026, 9, 1, tzinfo=UTC)
    candle_volumes = volumes or ["10"] * len(closes)
    return tuple(
        MarketCandle(
            open_time=start + timedelta(hours=index),
            close_time=start + timedelta(hours=index + 1),
            open=close,
            high=Decimal(close) + Decimal("1"),
            low=Decimal(close) - Decimal("1"),
            close=close,
            volume=candle_volumes[index],
            quote_volume=Decimal(candle_volumes[index]) * Decimal(close),
        )
        for index, close in enumerate(closes)
    )


def test_valid_research_plan_derives_bounded_candle_limit() -> None:
    plan = MarketResearchPlan(
        candidate_limit=5,
        timeframes=[ResearchTimeframe.H4, ResearchTimeframe.D1],
        lookback_days=30,
        priorities=[
            ResearchPriority.MOMENTUM,
            ResearchPriority.DOWNSIDE_CONTROL,
        ],
    )

    assert candle_limit(plan, ResearchTimeframe.H4) == 180
    assert candle_limit(plan, ResearchTimeframe.D1) == 30


@pytest.mark.parametrize(
    "values",
    [
        {
            "candidate_limit": 5,
            "timeframes": [ResearchTimeframe.M15],
            "lookback_days": 30,
            "priorities": [ResearchPriority.MOMENTUM],
        },
        {
            "candidate_limit": 5,
            "timeframes": [ResearchTimeframe.D1],
            "lookback_days": 10,
            "priorities": [ResearchPriority.MOMENTUM],
        },
        {
            "candidate_limit": 5,
            "timeframes": [
                ResearchTimeframe.H1,
                ResearchTimeframe.H4,
                ResearchTimeframe.D1,
            ],
            "lookback_days": 30,
            "priorities": [ResearchPriority.MOMENTUM],
        },
        {
            "candidate_limit": 5,
            "timeframes": [ResearchTimeframe.H4],
            "lookback_days": 30,
            "priorities": [
                ResearchPriority.MOMENTUM,
                ResearchPriority.MOMENTUM,
            ],
        },
    ],
)
def test_invalid_or_excessive_research_plan_is_rejected(values: dict) -> None:
    with pytest.raises(ValidationError):
        MarketResearchPlan(**values)


def test_market_ranking_uses_quote_volume_and_excludes_unsafe_categories() -> None:
    ranked = rank_market_candidates(
        [
            _ticker("USDCUSDT", "1000"),
            _ticker("ETHUPUSDT", "900"),
            _ticker("BTCUSDT", "100"),
            _ticker("ETHUSDT", "200"),
            _ticker("SOLUSDT", "150"),
        ],
        limit=3,
    )

    assert [candidate.symbol for candidate in ranked] == [
        "ETHUSDT",
        "SOLUSDT",
        "BTCUSDT",
    ]


def test_candle_analysis_calculates_verifiable_indicators() -> None:
    candles = _candles(
        ["100"] * 10 + ["110"] * 10,
        ["10"] * 10 + ["20"] * 10,
    )

    result = analyze_candles(candles, ResearchTimeframe.H1)

    assert result.sample_size == 20
    assert result.return_percent == Decimal("10.0")
    assert result.trend is TrendDirection.BULLISH
    assert result.realized_volatility_percent > 0
    assert result.max_drawdown_percent == Decimal("0")
    assert result.volume_change_percent == Decimal("100")


def test_candle_analysis_measures_drawdown_from_prior_peak() -> None:
    candles = _candles(["100", "120", "90"] + ["90"] * 17)

    result = analyze_candles(candles, ResearchTimeframe.H1)

    assert result.max_drawdown_percent == Decimal("25.00")
