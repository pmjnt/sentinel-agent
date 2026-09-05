from decimal import Decimal

from app.models.policy import PolicyPatch, PortfolioPolicy


def format_policy_update(
    patch: PolicyPatch,
    updated: PortfolioPolicy,
) -> str:
    """Describe only policy fields explicitly changed by the user."""
    changes: list[str] = []
    fields = patch.model_fields_set

    if "min_stablecoin_weight" in fields:
        if updated.min_stablecoin_weight is None:
            changes.append("removed the minimum stablecoin allocation")
        else:
            changes.append(
                "minimum stablecoin allocation is "
                f"{_format_percent(updated.min_stablecoin_weight)}"
            )

    if "max_asset_weight" in fields:
        if updated.max_asset_weight is None:
            changes.append("removed the maximum allocation per crypto asset")
        else:
            changes.append(
                "maximum allocation per crypto asset is "
                f"{_format_percent(updated.max_asset_weight)}"
            )

    if "block_high_volatility" in fields:
        if updated.block_high_volatility:
            changes.append("block rebalancing when market volatility is HIGH")
        else:
            changes.append(
                "allow rebalance evaluation when volatility is HIGH; "
                "RiskEngine still checks all other rules"
            )

    if "max_trade_usd_without_approval" in fields:
        threshold = updated.max_trade_usd_without_approval
        if threshold is None:
            changes.append("removed the approval threshold")
        else:
            changes.append(
                f"a proposal over {_format_usd(threshold)} requires approval"
            )

    if not changes:
        return "No policy changes were applied."
    return "Policy updated: " + "; ".join(changes) + "."


def format_current_policy(policy: PortfolioPolicy) -> str:
    """Return a readable English summary of the current policy."""
    if _is_empty_policy(policy):
        return "The current policy does not contain any portfolio limits."

    lines = ["Current policy:"]
    if policy.min_stablecoin_weight is not None:
        lines.append(
            "- Minimum stablecoin allocation: "
            f"{_format_percent(policy.min_stablecoin_weight)}"
        )
    if policy.max_asset_weight is not None:
        lines.append(
            "- Maximum allocation per crypto asset: "
            f"{_format_percent(policy.max_asset_weight)}"
        )
    lines.append(
        "- Rebalancing during HIGH volatility: "
        + ("BLOCKED" if policy.block_high_volatility else "allowed")
    )
    if policy.max_trade_usd_without_approval is not None:
        lines.append(
            "- Proposal requires approval above: "
            f"{_format_usd(policy.max_trade_usd_without_approval)}"
        )
    return "\n".join(lines)


def _is_empty_policy(policy: PortfolioPolicy) -> bool:
    return (
        policy.min_stablecoin_weight is None
        and policy.max_asset_weight is None
        and not policy.block_high_volatility
        and policy.max_trade_usd_without_approval is None
    )


def _format_percent(value: Decimal) -> str:
    percentage = format(value * Decimal("100"), "f").rstrip("0").rstrip(".")
    return f"{percentage}%"


def _format_usd(value: Decimal) -> str:
    formatted = f"{value:,.2f}"
    if formatted.endswith(".00"):
        formatted = formatted[:-3]
    return f"${formatted}"
