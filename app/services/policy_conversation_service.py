from dataclasses import dataclass
from typing import Protocol

from app.models.chat import (
    AnalyzePortfolioAction,
    ClarificationAction,
    ParsedRequest,
    UpdatePolicyAction,
    ViewPolicyAction,
)
from app.models.policy import PortfolioPolicy
from app.services.policy_response_service import (
    format_current_policy,
    format_policy_update,
)
from app.sessions import InMemoryPolicySessionStore


class RequestInterpreter(Protocol):
    async def interpret(
        self,
        message: str,
        current_policy: PortfolioPolicy,
    ) -> ParsedRequest: ...


@dataclass(frozen=True)
class PolicyConversationResult:
    message: str
    policy: PortfolioPolicy
    analysis_requested: bool
    focus_symbols: list[str]


class PolicyConversationService:
    """Execute validated policy-chat actions in their requested order."""

    def __init__(
        self,
        interpreter: RequestInterpreter,
        store: InMemoryPolicySessionStore,
    ) -> None:
        self._interpreter = interpreter
        self._store = store

    async def handle(
        self,
        session_id: str,
        message: str,
    ) -> PolicyConversationResult:
        policy = self._store.get(session_id)
        interpreted = await self._interpreter.interpret(message, policy)
        response_parts: list[str] = []
        analysis_requested = False
        focus_symbols: list[str] = []

        for action in interpreted.actions:
            if isinstance(action, ClarificationAction):
                return PolicyConversationResult(
                    message=action.question,
                    policy=policy,
                    analysis_requested=False,
                    focus_symbols=[],
                )

            if isinstance(action, UpdatePolicyAction):
                policy = self._store.apply(session_id, action.patch)
                response_parts.append(format_policy_update(action.patch, policy))
                continue

            if isinstance(action, ViewPolicyAction):
                response_parts.append(format_current_policy(policy))
                continue

            if isinstance(action, AnalyzePortfolioAction):
                analysis_requested = True
                for symbol in action.focus_symbols:
                    if symbol not in focus_symbols:
                        focus_symbols.append(symbol)

        if analysis_requested and not response_parts:
            response_parts.append("Đã ghi nhận yêu cầu phân tích portfolio.")

        return PolicyConversationResult(
            message="\n".join(response_parts),
            policy=policy,
            analysis_requested=analysis_requested,
            focus_symbols=focus_symbols,
        )
