from app.models.analysis import PortfolioAnalysis


def format_authoritative_analysis(analysis: PortfolioAnalysis) -> str:
    """Render financial facts in Python so LLM prose is never authoritative."""
    lines = [
        "Verified facts (Binance Demo)",
        f"- Total portfolio: ${analysis.portfolio.total_usd_value:,.2f}",
    ]
    for asset in analysis.portfolio.assets:
        weight_percent = asset.weight * 100
        lines.append(
            f"- {asset.symbol}: ${asset.usd_value:,.2f} ({weight_percent:.2f}%)"
        )

    if analysis.market_data:
        lines.append("- Market:")
        for market in analysis.market_data:
            lines.append(
                f"  - {market.symbol}: ${market.price:,.2f}, "
                f"24h {market.change_24h_percent}%, "
                f"volatility {market.volatility.value}, "
                f"estimated slippage {market.estimated_slippage_percent}%"
            )

    if analysis.violations:
        lines.append("- Policy violations:")
        for violation in analysis.violations:
            asset = f" {violation.asset}" if violation.asset else ""
            lines.append(f"  - {violation.type.value}{asset}: {violation.explanation}")
    else:
        lines.append("- Policy violations: none")

    if analysis.plan.actions:
        lines.append("- Proposed actions (not executed):")
        for action in analysis.plan.actions:
            lines.append(
                f"  - {action.side.value} {action.symbol}: "
                f"{action.amount} (~${action.estimated_usd_value:,.2f})"
            )
    else:
        lines.append("- Proposed actions: none")

    lines.append(f"- Risk Engine: {analysis.risk_decision.status.value}")
    for reason in analysis.risk_decision.reasons:
        lines.append(f"  - {reason}")
    lines.append("- Execution: NOT_EXECUTED")
    return "\n".join(lines)
