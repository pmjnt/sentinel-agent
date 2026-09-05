from decimal import Decimal

import pytest

from app.models.profile import InvestmentObjective, InvestorProfile, InvestorProfilePatch
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.sessions import InMemoryInvestorProfileSessionStore, InMemoryPolicySessionStore


def test_unknown_session_returns_empty_policy() -> None:
    store = InMemoryPolicySessionStore()

    assert store.get("session-1") == PortfolioPolicy()


def test_policy_updates_are_isolated_by_session() -> None:
    store = InMemoryPolicySessionStore()

    updated = store.apply(
        "session-1",
        PolicyPatch(max_asset_weight=Decimal("0.40")),
    )

    assert updated.max_asset_weight == Decimal("0.40")
    assert store.get("session-1").max_asset_weight == Decimal("0.40")
    assert store.get("session-2") == PortfolioPolicy()


def test_blank_session_id_is_rejected() -> None:
    store = InMemoryPolicySessionStore()

    with pytest.raises(ValueError, match="must not be empty"):
        store.get("   ")


def test_clear_removes_session_policy() -> None:
    store = InMemoryPolicySessionStore()
    store.apply(
        "session-1",
        PolicyPatch(min_stablecoin_weight=Decimal("0.30")),
    )

    store.clear("session-1")

    assert store.get("session-1") == PortfolioPolicy()


def test_apply_many_commits_validated_patches_in_order() -> None:
    store = InMemoryPolicySessionStore()

    result = store.apply_many(
        "session-1",
        (
            PolicyPatch(max_asset_weight=Decimal("0.50")),
            PolicyPatch(max_asset_weight=Decimal("0.40")),
        ),
        expected_policy=PortfolioPolicy(),
    )

    assert result.max_asset_weight == Decimal("0.40")
    assert store.get("session-1") == result


def test_apply_many_rejects_stale_policy_without_mutating_current_state() -> None:
    store = InMemoryPolicySessionStore()
    current = store.apply(
        "session-1",
        PolicyPatch(min_stablecoin_weight=Decimal("0.30")),
    )

    with pytest.raises(RuntimeError, match="changed during Agent run"):
        store.apply_many(
            "session-1",
            (PolicyPatch(max_asset_weight=Decimal("0.40")),),
            expected_policy=PortfolioPolicy(),
        )

    assert store.get("session-1") == current


def test_profile_store_isolates_sessions_and_rejects_stale_commit() -> None:
    store = InMemoryInvestorProfileSessionStore()
    empty = InvestorProfile()
    growth = store.apply_many(
        "user-1",
        (InvestorProfilePatch(objective=InvestmentObjective.GROWTH),),
        expected_profile=empty,
    )

    assert growth.objective is InvestmentObjective.GROWTH
    assert store.get("user-2") == empty

    with pytest.raises(RuntimeError, match="Profile changed"):
        store.apply_many(
            "user-1",
            (InvestorProfilePatch(time_horizon_months=36),),
            expected_profile=empty,
        )

    assert store.get("user-1") == growth
