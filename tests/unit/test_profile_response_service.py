from decimal import Decimal

from app.models.profile import (
    InvestmentObjective,
    InvestorProfile,
    InvestorProfilePatch,
    RiskTolerance,
)
from app.services.profile_response_service import (
    format_current_profile,
    format_profile_update,
)


def test_current_profile_is_readable_text_not_json() -> None:
    profile = InvestorProfile(
        objective=InvestmentObjective.GROWTH,
        time_horizon_months=36,
        risk_tolerance=RiskTolerance.MEDIUM,
        acceptable_loss_percent=Decimal("20"),
    )

    message = format_current_profile(profile)

    assert "Current investor profile:" in message
    assert "- Objective: growth" in message
    assert "- Time horizon: 36 months" in message
    assert "{" not in message


def test_profile_update_describes_changed_value() -> None:
    profile = InvestorProfile(objective=InvestmentObjective.GROWTH)

    message = format_profile_update(
        InvestorProfilePatch(objective=InvestmentObjective.GROWTH),
        profile,
    )

    assert message == "Investor profile updated: objective is growth."
