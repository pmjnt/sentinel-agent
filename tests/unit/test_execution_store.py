from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.execution.store import InMemoryExecutionPlanStore, PlanStateError
from app.models.execution import ExecutionPlan, ExecutionPlanStatus
from app.models.trade import TradeSide


def _plan(
    *,
    expires_in: int = 300,
    status: ExecutionPlanStatus = ExecutionPlanStatus.PENDING_APPROVAL,
) -> ExecutionPlan:
    now = datetime.now(UTC)
    requires_override = status is ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL
    return ExecutionPlan(
        plan_id="PLAN-ABC123",
        session_id="session-1",
        symbol="LINKUSDT" if requires_override else "BTCUSDT",
        side=TradeSide.BUY,
        quote_usd=Decimal("50"),
        estimated_quantity=Decimal("0.0005"),
        estimated_price=Decimal("100000"),
        reason="Add limited BTC exposure.",
        created_at=now,
        expires_at=now + timedelta(seconds=expires_in),
        status=status,
        requires_symbol_override=requires_override,
    )


def test_store_approves_exact_pending_plan_once() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan())

    approved = store.approve("session-1", "PLAN-ABC123")

    assert approved.status is ExecutionPlanStatus.APPROVED
    with pytest.raises(PlanStateError, match="APPROVED"):
        store.approve("session-1", "PLAN-ABC123")


def test_store_rejects_non_default_plan_that_skips_symbol_approval() -> None:
    store = InMemoryExecutionPlanStore()
    inconsistent = _plan().model_copy(
        update={"symbol": "LINKUSDT", "requires_symbol_override": False}
    )

    with pytest.raises(PlanStateError, match="approval state is inconsistent"):
        store.create(inconsistent)


def test_store_rejects_cross_session_access() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan())

    with pytest.raises(KeyError):
        store.get("another-session", "PLAN-ABC123")


def test_store_rejects_expired_plan() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan(expires_in=-1))

    with pytest.raises(PlanStateError, match="expired"):
        store.approve("session-1", "PLAN-ABC123")

    assert store.get("session-1", "PLAN-ABC123").status is ExecutionPlanStatus.EXPIRED


def test_symbol_override_must_be_approved_before_order_approval() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan(status=ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL))

    with pytest.raises(PlanStateError, match="PENDING_SYMBOL_APPROVAL"):
        store.approve("session-1", "PLAN-ABC123")

    pending_order_approval = store.approve_symbol_override(
        "session-1", "PLAN-ABC123"
    )

    assert pending_order_approval.status is ExecutionPlanStatus.PENDING_APPROVAL
    assert store.approve("session-1", "PLAN-ABC123").status is ExecutionPlanStatus.APPROVED


def test_repeated_symbol_override_approval_is_safe_and_idempotent() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan(status=ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL))
    first = store.approve_symbol_override("session-1", "PLAN-ABC123")

    second = store.approve_symbol_override("session-1", "PLAN-ABC123")

    assert second is first
    assert second.status is ExecutionPlanStatus.PENDING_APPROVAL


def test_expired_symbol_override_cannot_be_approved() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(
        _plan(
            expires_in=-1,
            status=ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL,
        )
    )

    with pytest.raises(PlanStateError, match="expired"):
        store.approve_symbol_override("session-1", "PLAN-ABC123")

    assert store.get("session-1", "PLAN-ABC123").status is ExecutionPlanStatus.EXPIRED


def test_override_pending_plan_can_be_rejected() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan(status=ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL))

    rejected = store.reject("session-1", "PLAN-ABC123")

    assert rejected.status is ExecutionPlanStatus.REJECTED


@pytest.mark.parametrize(
    "status",
    [
        ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL,
        ExecutionPlanStatus.PENDING_APPROVAL,
    ],
)
def test_expired_pending_plan_cannot_be_rejected(
    status: ExecutionPlanStatus,
) -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan(expires_in=-1, status=status))

    with pytest.raises(PlanStateError, match="expired"):
        store.reject("session-1", "PLAN-ABC123")

    assert store.get("session-1", "PLAN-ABC123").status is ExecutionPlanStatus.EXPIRED


def test_store_returns_saved_executed_plan_without_new_transition() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan())
    store.approve("session-1", "PLAN-ABC123")
    store.start_execution("session-1", "PLAN-ABC123")
    executed = store.finish_execution(
        "session-1",
        "PLAN-ABC123",
        order_id=42,
        order_status="FILLED",
    )

    assert executed.status is ExecutionPlanStatus.EXECUTED
    assert store.get("session-1", "PLAN-ABC123") is executed
