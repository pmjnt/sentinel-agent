from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.policy import (
    PolicyPatch,
    PortfolioPolicy,
    ViolationType,
)
from app.models.portfolio import Portfolio, PortfolioAsset
from app.services.policy_service import apply_policy_patch, find_policy_violations
from app.services.portfolio_service import calculate_portfolio


def _portfolio(values: dict[str, str]) -> Portfolio:
    return calculate_portfolio(
        [
            PortfolioAsset(
                symbol=symbol,
                amount=Decimal(value),
                usd_value=Decimal(value),
            )
            for symbol, value in values.items()
        ]
    )


def test_patch_changes_only_explicit_fields() -> None:
    current = PortfolioPolicy(
        min_stablecoin_weight=Decimal("0.30"),
        max_asset_weight=Decimal("0.40"),
        block_high_volatility=True,
        max_trade_usd_without_approval=Decimal("1000"),
    )

    updated = apply_policy_patch(
        current,
        PolicyPatch(max_asset_weight=Decimal("0.45")),
    )

    assert updated.max_asset_weight == Decimal("0.45")
    assert updated.min_stablecoin_weight == Decimal("0.30")
    assert updated.block_high_volatility is True
    assert updated.max_trade_usd_without_approval == Decimal("1000")


def test_patch_applies_execution_limits_without_changing_other_rules() -> None:
    current = PortfolioPolicy(max_asset_weight=Decimal("0.40"))

    updated = apply_policy_patch(
        current,
        PolicyPatch(
            max_trade_usd=Decimal("75"),
            max_slippage_percent=Decimal("0.10"),
            allowed_trade_symbols=("btcusdt",),
        ),
    )

    assert updated.max_asset_weight == Decimal("0.40")
    assert updated.max_trade_usd == Decimal("75")
    assert updated.max_slippage_percent == Decimal("0.10")
    assert updated.allowed_trade_symbols == ("BTCUSDT",)


def test_slippage_policy_is_a_percentage_between_zero_and_one_hundred() -> None:
    with pytest.raises(ValidationError):
        PortfolioPolicy(max_slippage_percent=Decimal("101"))


def test_explicit_null_removes_optional_rule() -> None:
    current = PortfolioPolicy(min_stablecoin_weight=Decimal("0.30"))

    updated = apply_policy_patch(
        current,
        PolicyPatch(min_stablecoin_weight=None),
    )

    assert updated.min_stablecoin_weight is None


def test_detects_max_asset_and_min_stablecoin_violations() -> None:
    portfolio = _portfolio({"BTC": "5500", "ETH": "2500", "USDT": "2000"})
    policy = PortfolioPolicy(
        min_stablecoin_weight=Decimal("0.30"),
        max_asset_weight=Decimal("0.40"),
    )

    violations = find_policy_violations(portfolio, policy)

    assert [violation.type for violation in violations] == [
        ViolationType.MAX_ASSET_WEIGHT,
        ViolationType.MIN_STABLECOIN_WEIGHT,
    ]
    assert violations[0].asset == "BTC"
    assert violations[0].current_value == Decimal("0.55")
    assert violations[0].allowed_value == Decimal("0.40")
    assert violations[1].asset == "USDT"
    assert violations[1].current_value == Decimal("0.20")
    assert violations[1].allowed_value == Decimal("0.30")


def test_compliant_portfolio_has_no_violations() -> None:
    portfolio = _portfolio({"BTC": "4000", "ETH": "3000", "USDT": "3000"})
    policy = PortfolioPolicy(
        min_stablecoin_weight=Decimal("0.30"),
        max_asset_weight=Decimal("0.40"),
    )

    assert find_policy_violations(portfolio, policy) == []


def test_max_asset_rule_excludes_configured_stablecoins() -> None:
    portfolio = _portfolio({"BTC": "2000", "USDT": "8000"})
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))

    assert find_policy_violations(portfolio, policy) == []
