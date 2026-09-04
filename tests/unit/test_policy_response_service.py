from decimal import Decimal

from app.models.policy import PolicyPatch, PortfolioPolicy
from app.services.policy_response_service import (
    format_current_policy,
    format_policy_update,
)


def test_formats_maximum_asset_weight_update() -> None:
    patch = PolicyPatch(max_asset_weight=Decimal("0.40"))
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))

    message = format_policy_update(patch, policy)

    assert "tỷ trọng tối đa" in message
    assert "40%" in message


def test_formats_removed_stablecoin_minimum() -> None:
    patch = PolicyPatch(min_stablecoin_weight=None)

    message = format_policy_update(patch, PortfolioPolicy())

    assert "đã bỏ" in message
    assert "stablecoin" in message


def test_formats_high_volatility_block_changes() -> None:
    enabled = format_policy_update(
        PolicyPatch(block_high_volatility=True),
        PortfolioPolicy(block_high_volatility=True),
    )
    disabled = format_policy_update(
        PolicyPatch(block_high_volatility=False),
        PortfolioPolicy(block_high_volatility=False),
    )

    assert "chặn rebalance" in enabled
    assert "cho phép đánh giá rebalance" in disabled


def test_formats_approval_threshold_with_currency_separator() -> None:
    patch = PolicyPatch(max_trade_usd_without_approval=Decimal("1000"))
    policy = PortfolioPolicy(
        max_trade_usd_without_approval=Decimal("1000")
    )

    message = format_policy_update(patch, policy)

    assert "$1,000" in message
    assert "phê duyệt" in message


def test_formats_empty_and_configured_policy_views() -> None:
    empty = format_current_policy(PortfolioPolicy())
    configured = format_current_policy(
        PortfolioPolicy(
            min_stablecoin_weight=Decimal("0.30"),
            max_asset_weight=Decimal("0.40"),
            block_high_volatility=True,
            max_trade_usd_without_approval=Decimal("1000"),
        )
    )

    assert "chưa có giới hạn" in empty
    assert "30%" in configured
    assert "40%" in configured
    assert "$1,000" in configured
