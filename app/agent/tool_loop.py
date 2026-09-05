import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from agents import (
    Agent,
    ModelBehaviorError,
    RunConfig,
    Runner,
    SessionSettings,
    set_tracing_disabled,
)

from app.agent.conversation_memory import (
    ConversationSessionStore,
    filter_conversation_history,
)
from app.agent.controlled_tools import CONTROLLED_TOOLS, MAX_MARKET_OBSERVATIONS
from app.agent.model_settings import build_agent_model_settings
from app.agent.output_safety import (
    validate_non_analysis_output,
    validate_qualitative_output,
)
from app.agent.prompts import CONTROLLED_TOOL_LOOP_INSTRUCTIONS
from app.agent.run_context import SentinelRunContext, SentinelRunEvent
from app.agent.streaming import ToolActivityTracker
from app.config import Settings
from app.gateways import PortfolioMarketGateway
from app.models.analysis import PortfolioAnalysis
from app.models.api import ActivityEvent
from app.models.profile import InvestorProfile, InvestorProfilePatch
from app.models.policy import PolicyPatch, PortfolioPolicy


RunAgent = Callable[..., Awaitable[Any]]
RunStreamedAgent = Callable[..., Any]
MAX_AGENT_TURNS = MAX_MARKET_OBSERVATIONS + 8
_FINANCIAL_OBSERVATION_REQUEST = re.compile(
    r"\b(?:analy[sz]e|analysis|risk|risky|exposure|holdings?|balances?|"
    r"market\s+(?:data|price)|price|volatility)\b"
    r"|phân tích|rủi ro|số dư|giá thị trường|biến động"
    r"|lời khuyên.{0,24}(?:đầu tư|tài khoản|danh mục)"
    r"|khuyến nghị.{0,24}(?:đầu tư|tài khoản|danh mục)"
    r"|investment advice|portfolio recommendation"
    r"|recommend.{0,24}(?:portfolio|account|invest)"
    r"|xem.{0,20}danh mục|tỷ trọng.{0,20}(?:hiện tại|của tôi)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ToolLoopResult:
    final_text: str
    events: tuple[SentinelRunEvent, ...]
    policy_patches: tuple[PolicyPatch, ...]
    final_policy: PortfolioPolicy
    profile_patches: tuple[InvestorProfilePatch, ...]
    final_profile: InvestorProfile
    analyses: tuple[PortfolioAnalysis, ...]
    data_errors: tuple[str, ...]


@dataclass(frozen=True)
class ToolLoopStreamCompleted:
    result: ToolLoopResult


def create_tool_loop_agent(settings: Settings) -> Agent[SentinelRunContext]:
    set_tracing_disabled(True)
    return Agent[SentinelRunContext](
        name="Sentinel",
        model=settings.agents_model,
        model_settings=build_agent_model_settings(settings),
        instructions=CONTROLLED_TOOL_LOOP_INSTRUCTIONS,
        tools=CONTROLLED_TOOLS,
    )


def build_tool_loop_input(
    message: str,
    policy: PortfolioPolicy,
    profile: InvestorProfile | None = None,
) -> str:
    normalized = message.strip()
    if not normalized:
        raise ValueError("Request message must not be empty.")
    return (
        "Current validated portfolio policy:\n"
        f"{policy.model_dump_json()}\n\n"
        "Current validated investor profile:\n"
        f"{(profile or InvestorProfile()).model_dump_json()}\n\n"
        "User message:\n"
        f"{normalized}"
    )


class SentinelToolLoop:
    def __init__(
        self,
        settings: Settings,
        gateway: PortfolioMarketGateway,
        run_agent: RunAgent | None = None,
        run_streamed_agent: RunStreamedAgent | None = None,
        conversation_sessions: ConversationSessionStore | None = None,
    ) -> None:
        self._agent = create_tool_loop_agent(settings)
        self._gateway = gateway
        self._run_agent = run_agent or Runner.run
        self._run_streamed_agent = run_streamed_agent or Runner.run_streamed
        self._conversation_sessions = (
            conversation_sessions or ConversationSessionStore()
        )
        self._run_config = RunConfig(
            session_input_callback=filter_conversation_history,
            session_settings=SessionSettings(limit=100),
        )

    async def run(
        self,
        message: str,
        policy: PortfolioPolicy,
        session_id: str = "default",
        profile: InvestorProfile | None = None,
    ) -> ToolLoopResult:
        current_profile = profile or InvestorProfile()
        context = SentinelRunContext.create(
            self._gateway,
            policy,
            current_profile,
        )
        result = await self._run_agent(
            self._agent,
            build_tool_loop_input(message, policy, current_profile),
            context=context,
            max_turns=MAX_AGENT_TURNS,
            session=self._conversation_sessions.get(session_id),
            run_config=self._run_config,
        )
        return self._build_result(message, context, result.final_output)

    async def stream(
        self,
        message: str,
        policy: PortfolioPolicy,
        session_id: str = "default",
        profile: InvestorProfile | None = None,
    ) -> AsyncIterator[ActivityEvent | ToolLoopStreamCompleted]:
        current_profile = profile or InvestorProfile()
        context = SentinelRunContext.create(self._gateway, policy, current_profile)
        result = self._run_streamed_agent(
            self._agent,
            build_tool_loop_input(message, policy, current_profile),
            context=context,
            max_turns=MAX_AGENT_TURNS,
            session=self._conversation_sessions.get(session_id),
            run_config=self._run_config,
        )
        tracker = ToolActivityTracker()
        async for event in result.stream_events():
            activity = tracker.consume(event)
            if activity is not None:
                yield activity
        yield ToolLoopStreamCompleted(
            self._build_result(message, context, result.final_output)
        )

    @staticmethod
    def _build_result(
        message: str,
        context: SentinelRunContext,
        output: object,
    ) -> ToolLoopResult:
        if not isinstance(output, str):
            raise ModelBehaviorError("Sentinel Agent must return text output.")

        final_text = output.strip()
        if context.analyses:
            final_text = validate_qualitative_output(final_text)
        else:
            final_text = validate_non_analysis_output(final_text)
            observed_financial_data = (
                context.portfolio is not None or bool(context.market_by_symbol)
            )
            if observed_financial_data and not context.data_errors:
                raise ModelBehaviorError(
                    "Sentinel Agent stopped before deterministic evaluation."
                )
            if (
                _FINANCIAL_OBSERVATION_REQUEST.search(message)
                and not context.data_errors
            ):
                raise ModelBehaviorError(
                    "Sentinel Agent answered a financial request "
                    "without deterministic analysis."
                )

        return ToolLoopResult(
            final_text=final_text,
            events=tuple(context.ordered_events),
            policy_patches=tuple(context.policy_patches),
            final_policy=context.working_policy,
            profile_patches=tuple(context.profile_patches),
            final_profile=context.working_profile,
            analyses=tuple(context.analyses),
            data_errors=tuple(context.data_errors),
        )
