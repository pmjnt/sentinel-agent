from decimal import Decimal

from app.models.policy import (
    PolicyPatch,
    PolicyViolation,
    PortfolioPolicy,
    ViolationSeverity,
    ViolationType,
)
from app.models.portfolio import Portfolio


DEFAULT_STABLECOINS = frozenset({"USDT"})


def apply_policy_patch(
    current: PortfolioPolicy,
    patch: PolicyPatch,
) -> PortfolioPolicy:
    """Apply only fields explicitly supplied in a policy update."""
    changes = patch.model_dump(include=patch.model_fields_set)
    if (
        "block_high_volatility" in changes
        and changes["block_high_volatility"] is None
    ):
        changes["block_high_volatility"] = False
    return current.model_copy(update=changes)


def find_policy_violations(
    portfolio: Portfolio,
    policy: PortfolioPolicy,
    stablecoin_symbols: frozenset[str] = DEFAULT_STABLECOINS,
) -> list[PolicyViolation]:
    """Compare deterministic portfolio weights with a validated policy."""
    stablecoins = frozenset(symbol.strip().upper() for symbol in stablecoin_symbols)
    violations: list[PolicyViolation] = []

    if policy.max_asset_weight is not None:
        violations.extend(
            _find_max_asset_violations(
                portfolio,
                policy.max_asset_weight,
                stablecoins,
            )
        )

    if policy.min_stablecoin_weight is not None:
        stablecoin_weight = sum(
            (
                asset.weight
                for asset in portfolio.assets
                if asset.symbol in stablecoins
            ),
            start=Decimal("0"),
        )
        if stablecoin_weight < policy.min_stablecoin_weight:
            violations.append(
                PolicyViolation(
                    type=ViolationType.MIN_STABLECOIN_WEIGHT,
                    asset="/".join(sorted(stablecoins)) or None,
                    current_value=stablecoin_weight,
                    allowed_value=policy.min_stablecoin_weight,
                    severity=ViolationSeverity.WARNING,
                    explanation=(
                        "Stablecoin allocation is below the configured minimum."
                    ),
                )
            )

    return violations


def _find_max_asset_violations(
    portfolio: Portfolio,
    maximum_weight: Decimal,
    stablecoins: frozenset[str],
) -> list[PolicyViolation]:
    return [
        PolicyViolation(
            type=ViolationType.MAX_ASSET_WEIGHT,
            asset=asset.symbol,
            current_value=asset.weight,
            allowed_value=maximum_weight,
            severity=ViolationSeverity.WARNING,
            explanation=(
                f"{asset.symbol} allocation exceeds the configured maximum."
            ),
        )
        for asset in portfolio.assets
        if asset.symbol not in stablecoins and asset.weight > maximum_weight
    ]
