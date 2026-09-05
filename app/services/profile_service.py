from app.models.profile import InvestorProfile, InvestorProfilePatch


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
