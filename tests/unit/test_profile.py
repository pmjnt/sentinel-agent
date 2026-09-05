from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.profile import (
    InvestmentObjective,
    InvestorProfile,
    InvestorProfilePatch,
    LiquidityNeed,
    RiskTolerance,
)
from app.services.profile_service import apply_profile_patch


def test_investor_profile_validates_and_normalizes_assets() -> None:
    profile = InvestorProfile(
        objective=InvestmentObjective.GROWTH,
        time_horizon_months=36,
        risk_tolerance=RiskTolerance.MEDIUM,
        acceptable_loss_percent=Decimal("20"),
        liquidity_need=LiquidityNeed.LOW,
        excluded_assets=[" xrp ", "XRP", "bnb"],
    )

    assert profile.excluded_assets == ["XRP", "BNB"]


def test_investor_profile_rejects_invalid_horizon_and_loss() -> None:
    with pytest.raises(ValidationError):
        InvestorProfile(time_horizon_months=0)
    with pytest.raises(ValidationError):
        InvestorProfile(acceptable_loss_percent=Decimal("101"))


def test_profile_patch_changes_only_explicit_fields_and_can_clear_value() -> None:
    current = InvestorProfile(
        objective=InvestmentObjective.GROWTH,
        time_horizon_months=36,
        excluded_assets=["XRP"],
    )

    updated = apply_profile_patch(
        current,
        InvestorProfilePatch(
            time_horizon_months=60,
            excluded_assets=None,
        ),
    )

    assert updated.objective is InvestmentObjective.GROWTH
    assert updated.time_horizon_months == 60
    assert updated.excluded_assets == []
