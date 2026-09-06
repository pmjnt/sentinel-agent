from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    PolicyViewedEvent,
    ProfileUpdatedEvent,
    ProfileViewedEvent,
    TradeProposedEvent,
)
from app.agent.tool_loop import ToolLoopResult, ToolLoopStreamCompleted
from app.execution.store import InMemoryExecutionPlanStore
from app.models.analysis import PortfolioAnalysis
from app.models.api import (
    ActivityEvent,
    ExecutionStatus,
    StructuredSentinelResponse,
    TextDeltaEvent,
)
from app.models.execution import ExecutionPlan, ExecutionPlanStatus
from app.model_catalog import ModelRoute
from app.models.profile import InvestorProfile
from app.models.policy import PortfolioPolicy
from app.services.execution_response_service import format_pending_execution_plan
from app.services.execution_service import DemoExecutionService
from app.services.analysis_response_service import format_authoritative_analysis
from app.services.policy_service import apply_policy_patch
from app.services.profile_response_service import (
    format_current_profile,
    format_profile_update,
)
from app.services.profile_service import apply_profile_patch
from app.services.policy_response_service import (
    format_current_policy,
    format_policy_update,
)
from app.sessions import InMemoryInvestorProfileSessionStore, InMemoryPolicySessionStore


class AgentLoop(Protocol):
    async def run(
        self,
        message: str,
        policy: PortfolioPolicy,
        session_id: str = "default",
        profile: InvestorProfile | None = None,
        model_route: ModelRoute | None = None,
    ) -> ToolLoopResult: ...


class SentinelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    policy: PortfolioPolicy
    profile: InvestorProfile = InvestorProfile()
    analyses: tuple[PortfolioAnalysis, ...] = ()
    ai_interpretation: str | None = None
    execution_plan: ExecutionPlan | None = None

    @property
    def analysis(self) -> PortfolioAnalysis | None:
        """Convenience access to the latest successful analysis, if any."""
        return self.analyses[-1] if self.analyses else None


class SentinelApplication:
    """Commit a successful Agent run and render authoritative output."""

    def __init__(
        self,
        agent_loop: AgentLoop,
        store: InMemoryPolicySessionStore,
        profile_store: InMemoryInvestorProfileSessionStore | None = None,
        execution_plans: InMemoryExecutionPlanStore | None = None,
        execution_service: DemoExecutionService | None = None,
    ) -> None:
        self._agent_loop = agent_loop
        self._store = store
        self._profile_store = profile_store or InMemoryInvestorProfileSessionStore()
        self._execution_plans = execution_plans or InMemoryExecutionPlanStore()
        self._execution_service = execution_service

    async def approve_plan(self, session_id: str, plan_id: str) -> ExecutionPlan:
        if self._execution_service is None:
            raise RuntimeError("Binance Demo execution is not configured.")
        return await self._execution_service.approve_and_execute(session_id, plan_id)

    def reject_plan(self, session_id: str, plan_id: str) -> ExecutionPlan:
        if self._execution_service is None:
            return self._execution_plans.reject(session_id, plan_id)
        return self._execution_service.reject(session_id, plan_id)

    async def handle(
        self,
        session_id: str,
        message: str,
        model_route: ModelRoute | None = None,
    ) -> SentinelResponse:
        starting_policy = self._store.get(session_id)
        starting_profile = self._profile_store.get(session_id)
        run_kwargs = {"profile": starting_profile}
        if model_route is not None:
            run_kwargs["model_route"] = model_route
        loop_result = await self._agent_loop.run(
            message,
            starting_policy,
            session_id,
            **run_kwargs,
        )
        return self._commit_and_render(
            session_id,
            starting_policy,
            starting_profile,
            loop_result,
        )

    async def stream_handle(
        self,
        session_id: str,
        message: str,
        model_route: ModelRoute | None = None,
    ) -> AsyncIterator[
        ActivityEvent | TextDeltaEvent | StructuredSentinelResponse
    ]:
        starting_policy = self._store.get(session_id)
        starting_profile = self._profile_store.get(session_id)
        activities: list[ActivityEvent] = []
        stream_kwargs = {"profile": starting_profile}
        if model_route is not None:
            stream_kwargs["model_route"] = model_route
        async for event in self._agent_loop.stream(
            message,
            starting_policy,
            session_id,
            **stream_kwargs,
        ):
            if isinstance(event, ActivityEvent):
                activities.append(event)
                yield event
                continue

            if not isinstance(event, ToolLoopStreamCompleted):
                continue
            response = self._commit_and_render(
                session_id,
                starting_policy,
                starting_profile,
                event.result,
            )
            display_text = response.ai_interpretation or response.message
            for chunk in _text_chunks(display_text):
                yield TextDeltaEvent(text=chunk)
            yield StructuredSentinelResponse(
                session_id=session_id,
                provider=(
                    model_route.provider.value
                    if model_route is not None
                    else None
                ),
                model=(model_route.model if model_route is not None else None),
                message=response.message,
                policy=response.policy,
                profile=response.profile,
                analysis=response.analysis,
                activity=activities,
                ai_interpretation=response.ai_interpretation,
                execution_status=(
                    _api_execution_status(response.execution_plan.status)
                    if response.execution_plan is not None
                    else ExecutionStatus.NOT_EXECUTED
                ),
                execution_plan=response.execution_plan,
            )

    def _commit_and_render(
        self,
        session_id: str,
        starting_policy: PortfolioPolicy,
        starting_profile: InvestorProfile,
        loop_result: ToolLoopResult,
    ) -> SentinelResponse:
        expected_final_policy = starting_policy
        for patch in loop_result.policy_patches:
            expected_final_policy = apply_policy_patch(expected_final_policy, patch)
        if expected_final_policy != loop_result.final_policy:
            raise RuntimeError("Agent policy state did not match staged patches.")
        expected_final_profile = starting_profile
        for patch in loop_result.profile_patches:
            expected_final_profile = apply_profile_patch(
                expected_final_profile,
                patch,
            )
        if expected_final_profile != loop_result.final_profile:
            raise RuntimeError("Agent profile state did not match staged patches.")

        committed_policy = self._store.apply_many(
            session_id,
            loop_result.policy_patches,
            expected_policy=starting_policy,
        )
        committed_profile = self._profile_store.apply_many(
            session_id,
            loop_result.profile_patches,
            expected_profile=starting_profile,
        )

        for plan in loop_result.execution_plans:
            if plan.session_id != session_id:
                raise RuntimeError("Execution plan session did not match Agent run.")
            self._execution_plans.create(plan)

        response_parts: list[str] = []
        for event in loop_result.events:
            if isinstance(event, PolicyUpdatedEvent):
                response_parts.append(
                    format_policy_update(event.patch, event.policy)
                )
                continue
            if isinstance(event, PolicyViewedEvent):
                response_parts.append(format_current_policy(event.policy))
                continue
            if isinstance(event, ProfileUpdatedEvent):
                response_parts.append(
                    format_profile_update(event.patch, event.profile)
                )
                continue
            if isinstance(event, ProfileViewedEvent):
                response_parts.append(format_current_profile(event.profile))
                continue
            if isinstance(event, AnalysisCompletedEvent):
                response_parts.append(format_authoritative_analysis(event.analysis))
                continue
            if isinstance(event, TradeProposedEvent):
                response_parts.append(format_pending_execution_plan(event.plan))

        if loop_result.data_errors:
            details = "\n".join(
                f"- {error}" for error in dict.fromkeys(loop_result.data_errors)
            )
            response_parts.append(
                "Required Binance Demo data could not be verified. "
                "Sentinel did not generate a recommendation or permit execution."
                f"\n{details}"
            )
        elif loop_result.analyses and loop_result.final_text:
            response_parts.append(f"AI interpretation:\n{loop_result.final_text}")
        elif not loop_result.events:
            response_parts.append(loop_result.final_text)

        return SentinelResponse(
            message=_join_messages(*response_parts),
            policy=committed_policy,
            profile=committed_profile,
            analyses=loop_result.analyses,
            ai_interpretation=(
                loop_result.final_text or None
                if loop_result.analyses
                else None
            ),
            execution_plan=(
                loop_result.execution_plans[-1]
                if loop_result.execution_plans
                else None
            ),
        )


def _join_messages(*messages: str) -> str:
    return "\n\n".join(message for message in messages if message)


def _text_chunks(text: str, size: int = 80) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)]


def _api_execution_status(status: ExecutionPlanStatus) -> ExecutionStatus:
    return ExecutionStatus(status.value)
