from app.models.profile import InvestorProfile, InvestorProfilePatch


def format_profile_update(
    patch: InvestorProfilePatch,
    profile: InvestorProfile,
) -> str:
    changes = [
        _format_field(field, getattr(profile, field))
        for field in sorted(patch.model_fields_set)
    ]
    return "Investor profile updated: " + "; ".join(changes) + "."


def format_current_profile(profile: InvestorProfile) -> str:
    if profile == InvestorProfile():
        return "The investor profile does not contain any preferences yet."
    lines = ["Current investor profile:"]
    for field in (
        "objective",
        "time_horizon_months",
        "risk_tolerance",
        "acceptable_loss_percent",
        "liquidity_need",
        "excluded_assets",
    ):
        value = getattr(profile, field)
        if value is not None and value != []:
            lines.append(f"- {_field_label(field)}: {_display_value(field, value)}")
    return "\n".join(lines)


def _format_field(field: str, value: object) -> str:
    label = _field_label(field).lower()
    if value is None or value == []:
        return f"removed {label}"
    return f"{label} is {_display_value(field, value)}"


def _field_label(field: str) -> str:
    return {
        "objective": "Objective",
        "time_horizon_months": "Time horizon",
        "risk_tolerance": "Risk tolerance",
        "acceptable_loss_percent": "Acceptable loss",
        "liquidity_need": "Liquidity need",
        "excluded_assets": "Excluded assets",
    }[field]


def _display_value(field: str, value: object) -> str:
    if field == "time_horizon_months":
        return f"{value} months"
    if field == "acceptable_loss_percent":
        return f"{value}%"
    if field == "excluded_assets":
        return ", ".join(value)  # type: ignore[arg-type]
    enum_value = getattr(value, "value", value)
    return str(enum_value).lower().replace("_", " ")
