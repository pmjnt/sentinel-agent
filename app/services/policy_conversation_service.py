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
class PolicyMessageEvent:
    message: str


@dataclass(frozen=True)
class PortfolioAnalysisEvent:
    policy: PortfolioPolicy
    focus_symbols: tuple[str, ...]


PolicyConversationEvent = PolicyMessageEvent | PortfolioAnalysisEvent


@dataclass(frozen=True)
class PolicyConversationResult:
    events: tuple[PolicyConversationEvent, ...]
    policy: PortfolioPolicy

    @property
    def message(self) -> str:
        return "\n".join(
            event.message
            for event in self.events
            if isinstance(event, PolicyMessageEvent)
        )

    @property
    def analysis_requested(self) -> bool:
        return any(
            isinstance(event, PortfolioAnalysisEvent) for event in self.events
        )

    @property
    def focus_symbols(self) -> list[str]:
        symbols: dict[str, None] = {}
        for event in self.events:
            if isinstance(event, PortfolioAnalysisEvent):
                for symbol in event.focus_symbols:
                    symbols[symbol] = None
        return list(symbols)


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
        events: list[PolicyConversationEvent] = []

        clarification = next(
            (
                action
                for action in interpreted.actions
                if isinstance(action, ClarificationAction)
            ),
            None,
        )
        if clarification is not None:
            return PolicyConversationResult(
                events=(PolicyMessageEvent(clarification.question),),
                policy=policy,
            )

        for action in interpreted.actions:
            if isinstance(action, UpdatePolicyAction):
                policy = self._store.apply(session_id, action.patch)
                events.append(
                    PolicyMessageEvent(format_policy_update(action.patch, policy))
                )
                continue

            if isinstance(action, ViewPolicyAction):
                events.append(PolicyMessageEvent(format_current_policy(policy)))
                continue

            if isinstance(action, AnalyzePortfolioAction):
                events.append(
                    PortfolioAnalysisEvent(
                        policy=policy,
                        focus_symbols=tuple(dict.fromkeys(action.focus_symbols)),
                    )
                )

        return PolicyConversationResult(
            events=tuple(events),
            policy=policy,
        )
