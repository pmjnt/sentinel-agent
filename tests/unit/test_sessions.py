from decimal import Decimal

import pytest

from app.models.policy import PolicyPatch, PortfolioPolicy
from app.sessions import InMemoryPolicySessionStore


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
