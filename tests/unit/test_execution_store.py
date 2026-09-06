from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.execution.store import InMemoryExecutionPlanStore, PlanStateError
from app.models.execution import ExecutionPlan, ExecutionPlanStatus
from app.models.trade import TradeSide


def _plan(*, expires_in: int = 300) -> ExecutionPlan:
    now = datetime.now(UTC)
    return ExecutionPlan(
        plan_id="PLAN-ABC123",
        session_id="session-1",
        symbol="BTCUSDT",
        side=TradeSide.BUY,
        quote_usd=Decimal("50"),
        estimated_quantity=Decimal("0.0005"),
        estimated_price=Decimal("100000"),
        reason="Add limited BTC exposure.",
        created_at=now,
        expires_at=now + timedelta(seconds=expires_in),
    )


def test_store_approves_exact_pending_plan_once() -> None:
    store = InMemoryExecutionPlanStore()
    store.create(_plan())

    approved = store.approve("session-1", "PLAN-ABC123")

    assert approved.status is ExecutionPlanStatus.APPROVED
    with pytest.raises(PlanStateError, match="APPROVED"):
        store.approve("session-1", "PLAN-ABC123")


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
