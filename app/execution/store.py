from datetime import UTC, datetime
from threading import Lock

from app.models.execution import ExecutionPlan, ExecutionPlanStatus
from app.services.trade_universe_service import DEFAULT_TRADE_SYMBOLS


class PlanStateError(RuntimeError):
    pass


class InMemoryExecutionPlanStore:
    def __init__(self) -> None:
        self._plans: dict[str, ExecutionPlan] = {}
        self._lock = Lock()

    def create(self, plan: ExecutionPlan) -> ExecutionPlan:
        with self._lock:
            if plan.plan_id in self._plans:
                raise PlanStateError("Plan ID already exists.")
            override_required = plan.symbol not in DEFAULT_TRADE_SYMBOLS
            expected_status = (
                ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL
                if override_required
                else ExecutionPlanStatus.PENDING_APPROVAL
            )
            if (
                plan.requires_symbol_override is not override_required
                or plan.status is not expected_status
            ):
                raise PlanStateError("Plan approval state is inconsistent.")
            self._plans[plan.plan_id] = plan
            return plan

    def get(self, session_id: str, plan_id: str) -> ExecutionPlan:
        plan = self._plans.get(plan_id)
        if plan is None or plan.session_id != session_id:
            raise KeyError("Execution plan was not found.")
        return plan

    def approve(self, session_id: str, plan_id: str) -> ExecutionPlan:
        with self._lock:
            plan = self.get(session_id, plan_id)
            if plan.status is not ExecutionPlanStatus.PENDING_APPROVAL:
                raise PlanStateError(f"Plan is already {plan.status.value}.")
            if datetime.now(UTC) >= plan.expires_at:
                expired = plan.model_copy(update={"status": ExecutionPlanStatus.EXPIRED})
                self._plans[plan_id] = expired
                raise PlanStateError("Execution plan has expired.")
            return self._replace(plan, ExecutionPlanStatus.APPROVED)

    def approve_symbol_override(
        self, session_id: str, plan_id: str
    ) -> ExecutionPlan:
        with self._lock:
            plan = self.get(session_id, plan_id)
            is_completed_override = (
                plan.status is ExecutionPlanStatus.PENDING_APPROVAL
                and plan.requires_symbol_override
            )
            if (
                plan.status is not ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL
                and not is_completed_override
            ):
                raise PlanStateError(f"Plan is already {plan.status.value}.")
            if datetime.now(UTC) >= plan.expires_at:
                expired = plan.model_copy(update={"status": ExecutionPlanStatus.EXPIRED})
                self._plans[plan_id] = expired
                raise PlanStateError("Execution plan has expired.")
            if is_completed_override:
                return plan
            return self._replace(plan, ExecutionPlanStatus.PENDING_APPROVAL)

    def reject(self, session_id: str, plan_id: str) -> ExecutionPlan:
        with self._lock:
            plan = self.get(session_id, plan_id)
            if plan.status not in {
                ExecutionPlanStatus.PENDING_SYMBOL_APPROVAL,
                ExecutionPlanStatus.PENDING_APPROVAL,
            }:
                raise PlanStateError(f"Plan is already {plan.status.value}.")
            if datetime.now(UTC) >= plan.expires_at:
                expired = plan.model_copy(update={"status": ExecutionPlanStatus.EXPIRED})
                self._plans[plan_id] = expired
                raise PlanStateError("Execution plan has expired.")
            return self._replace(plan, ExecutionPlanStatus.REJECTED)

    def start_execution(self, session_id: str, plan_id: str) -> ExecutionPlan:
        with self._lock:
            plan = self.get(session_id, plan_id)
            if plan.status is not ExecutionPlanStatus.APPROVED:
                raise PlanStateError(f"Plan is {plan.status.value}, not APPROVED.")
            return self._replace(plan, ExecutionPlanStatus.EXECUTING)

    def finish_execution(
        self,
        session_id: str,
        plan_id: str,
        *,
        order_id: int,
        order_status: str,
    ) -> ExecutionPlan:
        with self._lock:
            plan = self.get(session_id, plan_id)
            if plan.status is not ExecutionPlanStatus.EXECUTING:
                raise PlanStateError(f"Plan is {plan.status.value}, not EXECUTING.")
            updated = plan.model_copy(
                update={
                    "status": ExecutionPlanStatus.EXECUTED,
                    "order_id": order_id,
                    "order_status": order_status,
                }
            )
            self._plans[plan_id] = updated
            return updated

    def fail_execution(self, session_id: str, plan_id: str, reason: str) -> ExecutionPlan:
        with self._lock:
            plan = self.get(session_id, plan_id)
            updated = plan.model_copy(
                update={"status": ExecutionPlanStatus.FAILED, "failure_reason": reason}
            )
            self._plans[plan_id] = updated
            return updated

    def _replace(self, plan: ExecutionPlan, status: ExecutionPlanStatus) -> ExecutionPlan:
        updated = plan.model_copy(update={"status": status})
        self._plans[plan.plan_id] = updated
        return updated
