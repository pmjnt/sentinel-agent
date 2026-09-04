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
            changes.append("đã bỏ yêu cầu tỷ trọng stablecoin tối thiểu")
        else:
            changes.append(
                "tỷ trọng stablecoin tối thiểu là "
                f"{_format_percent(updated.min_stablecoin_weight)}"
            )

    if "max_asset_weight" in fields:
        if updated.max_asset_weight is None:
            changes.append("đã bỏ giới hạn tỷ trọng tối đa cho mỗi tài sản crypto")
        else:
            changes.append(
                "tỷ trọng tối đa cho mỗi tài sản crypto là "
                f"{_format_percent(updated.max_asset_weight)}"
            )

    if "block_high_volatility" in fields:
        if updated.block_high_volatility:
            changes.append("chặn rebalance khi thị trường có volatility HIGH")
        else:
            changes.append(
                "cho phép đánh giá rebalance khi volatility HIGH; "
                "RiskEngine vẫn kiểm tra các quy tắc khác"
            )

    if "max_trade_usd_without_approval" in fields:
        threshold = updated.max_trade_usd_without_approval
        if threshold is None:
            changes.append("đã bỏ ngưỡng giá trị cần phê duyệt")
        else:
            changes.append(
                f"proposal trên {_format_usd(threshold)} cần được phê duyệt"
            )

    if not changes:
        return "Không có thay đổi policy nào được áp dụng."
    return "Đã cập nhật policy: " + "; ".join(changes) + "."


def format_current_policy(policy: PortfolioPolicy) -> str:
    """Return a readable Vietnamese summary of the current policy."""
    if _is_empty_policy(policy):
        return "Policy hiện tại chưa có giới hạn portfolio nào."

    lines = ["Policy hiện tại:"]
    if policy.min_stablecoin_weight is not None:
        lines.append(
            "- Stablecoin tối thiểu: "
            f"{_format_percent(policy.min_stablecoin_weight)}"
        )
    if policy.max_asset_weight is not None:
        lines.append(
            "- Mỗi tài sản crypto tối đa: "
            f"{_format_percent(policy.max_asset_weight)}"
        )
    lines.append(
        "- Rebalance khi volatility HIGH: "
        + ("BỊ CHẶN" if policy.block_high_volatility else "không bị chặn")
    )
    if policy.max_trade_usd_without_approval is not None:
        lines.append(
            "- Proposal cần phê duyệt khi vượt: "
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
