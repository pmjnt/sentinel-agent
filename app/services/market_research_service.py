from decimal import Decimal

from app.models.research import (
    MarketCandle,
    MarketResearchPlan,
    MarketTicker,
    ResearchTimeframe,
    TimeframeResearch,
    TrendDirection,
)


_BARS_PER_DAY = {
    ResearchTimeframe.M15: 96,
    ResearchTimeframe.H1: 24,
    ResearchTimeframe.H4: 6,
    ResearchTimeframe.D1: 1,
}
_STABLECOINS = frozenset(
    {"USDT", "USDC", "FDUSD", "TUSD", "USDP", "DAI", "BUSD"}
)
_LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
_HUNDRED = Decimal("100")
_TREND_BAND = Decimal("0.005")


def candle_limit(
    plan: MarketResearchPlan,
    timeframe: ResearchTimeframe,
) -> int:
    if timeframe not in plan.timeframes:
        raise ValueError("Timeframe is not part of the active research plan.")
    return plan.lookback_days * _BARS_PER_DAY[timeframe]


def rank_market_candidates(
    tickers: list[MarketTicker] | tuple[MarketTicker, ...],
    *,
    limit: int,
) -> tuple[MarketTicker, ...]:
    if limit < 3 or limit > 10:
        raise ValueError("Candidate limit must be between 3 and 10.")
    eligible = [
        ticker
        for ticker in tickers
        if ticker.quote_volume > 0 and _is_research_candidate(ticker.symbol)
    ]
    eligible.sort(key=lambda ticker: (-ticker.quote_volume, ticker.symbol))
    return tuple(eligible[:limit])


def analyze_candles(
    candles: tuple[MarketCandle, ...] | list[MarketCandle],
    timeframe: ResearchTimeframe,
) -> TimeframeResearch:
    ordered = tuple(sorted(candles, key=lambda candle: candle.open_time))
    if len(ordered) < 20:
        raise ValueError("At least 20 candles are required for market research.")

    closes = [candle.close for candle in ordered]
    returns = [
        (current / previous - Decimal("1")) * _HUNDRED
        for previous, current in zip(closes, closes[1:])
    ]
    mean_return = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum(
        ((value - mean_return) ** 2 for value in returns),
        Decimal("0"),
    ) / Decimal(len(returns))

    peak = closes[0]
    max_drawdown = Decimal("0")
    for close in closes:
        peak = max(peak, close)
        drawdown = (peak - close) / peak * _HUNDRED
        max_drawdown = max(max_drawdown, drawdown)

    midpoint = len(ordered) // 2
    first_volume = _average([candle.volume for candle in ordered[:midpoint]])
    second_volume = _average([candle.volume for candle in ordered[midpoint:]])
    if first_volume == 0:
        raise ValueError("Candle volume baseline must be positive.")

    long_average = _average(closes)
    short_window = max(5, len(closes) // 4)
    short_average = _average(closes[-short_window:])
    relative_trend = short_average / long_average - Decimal("1")
    if relative_trend > _TREND_BAND:
        trend = TrendDirection.BULLISH
    elif relative_trend < -_TREND_BAND:
        trend = TrendDirection.BEARISH
    else:
        trend = TrendDirection.NEUTRAL

    return TimeframeResearch(
        timeframe=timeframe,
        sample_size=len(ordered),
        return_percent=(closes[-1] / closes[0] - Decimal("1")) * _HUNDRED,
        trend=trend,
        realized_volatility_percent=variance.sqrt(),
        max_drawdown_percent=max_drawdown,
        volume_change_percent=(second_volume / first_volume - Decimal("1"))
        * _HUNDRED,
    )


def _average(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))


def _is_research_candidate(symbol: str) -> bool:
    normalized = symbol.strip().upper()
    if not normalized.endswith("USDT"):
        return False
    base_asset = normalized.removesuffix("USDT")
    return (
        base_asset not in _STABLECOINS
        and not base_asset.endswith(_LEVERAGED_SUFFIXES)
    )
