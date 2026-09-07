from decimal import Decimal, ROUND_HALF_UP

from app.models.research import MarketResearchResult


_DISPLAY_STEP = Decimal("0.01")


def _display(value: Decimal) -> str:
    rounded = value.quantize(_DISPLAY_STEP, rounding=ROUND_HALF_UP)
    return format(rounded, "f")


def format_market_research(result: MarketResearchResult) -> str:
    """Render verified summaries only; raw Binance candles stay server-side."""
    plan = result.plan
    lines = [
        "Verified Binance market research",
        (
            f"- Plan: top {plan.candidate_limit} Spot USDT markets; "
            f"{plan.lookback_days} day(s); "
            f"timeframes {', '.join(item.value for item in plan.timeframes)}; "
            f"priorities {', '.join(item.value for item in plan.priorities)}"
        ),
        f"- Scan observed at: {result.scan.observed_at.isoformat()}",
        "- Top quote-volume candidates:",
    ]
    for candidate in result.scan.candidates:
        lines.append(
            f"  - {candidate.symbol}: ${candidate.quote_volume:,.2f} quote volume"
        )

    lines.append("- Deterministic historical indicators:")
    for candidate in result.analyzed_candidates:
        for timeframe in candidate.timeframes:
            lines.append(
                f"  - {candidate.candidate.symbol} {timeframe.timeframe.value}: "
                f"return {_display(timeframe.return_percent)}%, "
                f"trend {timeframe.trend.value}, "
                f"volatility {_display(timeframe.realized_volatility_percent)}%, "
                f"max drawdown {_display(timeframe.max_drawdown_percent)}%, "
                f"volume change {_display(timeframe.volume_change_percent)}%"
            )
    if result.failed_symbols:
        lines.append(
            "- Unavailable history: " + ", ".join(result.failed_symbols)
        )
    return "\n".join(lines)
