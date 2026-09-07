from app.models.profile import InvestorProfile, InvestorProfilePatch


def is_advice_profile_ready(profile: InvestorProfile) -> bool:
    """Return whether core preferences are sufficient for useful advice."""
    has_risk_measure = (
        profile.acceptable_loss_percent is not None
        or profile.risk_tolerance is not None
    )
    return (
        profile.objective is not None
        and profile.time_horizon_months is not None
        and has_risk_measure
    )


def apply_profile_patch(
    profile: InvestorProfile,
    patch: InvestorProfilePatch,
) -> InvestorProfile:
    """Apply only explicitly supplied, already validated profile fields."""
    updates = {
        field: getattr(patch, field)
        for field in patch.model_fields_set
    }
    if updates.get("excluded_assets") is None and "excluded_assets" in updates:
        updates["excluded_assets"] = []
    return profile.model_copy(update=updates)
