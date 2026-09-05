from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.agent.run_context import (
    AnalysisCompletedEvent,
    PolicyUpdatedEvent,
    PolicyViewedEvent,
)
from app.agent.tool_loop import ToolLoopResult
from app.models.analysis import PortfolioAnalysis
from app.models.policy import PortfolioPolicy
from app.services.analysis_response_service import format_authoritative_analysis
from app.services.policy_service import apply_policy_patch
from app.services.policy_response_service import (
    format_current_policy,
    format_policy_update,
)
from app.sessions import InMemoryPolicySessionStore


class AgentLoop(Protocol):
    async def run(
        self,
        message: str,
        policy: PortfolioPolicy,
        session_id: str = "default",
    ) -> ToolLoopResult: ...


class SentinelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    policy: PortfolioPolicy
    analyses: tuple[PortfolioAnalysis, ...] = ()

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
    ) -> None:
        self._agent_loop = agent_loop
        self._store = store

    async def handle(self, session_id: str, message: str) -> SentinelResponse:
        starting_policy = self._store.get(session_id)
        loop_result = await self._agent_loop.run(
            message,
            starting_policy,
            session_id,
        )
        expected_final_policy = starting_policy
        for patch in loop_result.policy_patches:
            expected_final_policy = apply_policy_patch(expected_final_policy, patch)
        if expected_final_policy != loop_result.final_policy:
            raise RuntimeError("Agent policy state did not match staged patches.")

        committed_policy = self._store.apply_many(
            session_id,
            loop_result.policy_patches,
            expected_policy=starting_policy,
        )

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
            if isinstance(event, AnalysisCompletedEvent):
                response_parts.append(format_authoritative_analysis(event.analysis))

        if loop_result.data_errors:
            response_parts.append(
                "Required Binance Demo data could not be verified. "
                "Sentinel did not generate a recommendation or permit execution."
            )
        elif loop_result.analyses:
            response_parts.append(f"AI interpretation:\n{loop_result.final_text}")
        elif not loop_result.events:
            response_parts.append(loop_result.final_text)

        return SentinelResponse(
            message=_join_messages(*response_parts),
            policy=committed_policy,
            analyses=loop_result.analyses,
        )


def _join_messages(*messages: str) -> str:
    return "\n\n".join(message for message in messages if message)
