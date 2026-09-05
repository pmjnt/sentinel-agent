from collections.abc import Awaitable, Callable
import re
from typing import Any

from agents import Agent, ModelBehaviorError, Runner, set_tracing_disabled

from app.agent.model_settings import build_agent_model_settings
from app.agent.prompts import ANALYSIS_REPORTER_INSTRUCTIONS
from app.config import Settings
from app.models.analysis import PortfolioAnalysis


RunAgent = Callable[..., Awaitable[Any]]

_RESERVED_REPORTER_LANGUAGE = re.compile(
    r"\bblocked\b"
    r"|\brequires?[\s_-]+approval\b"
    r"|\bsafe(?:[\s_-]+to)?[\s_-]+propose\b"
    r"|\bexecut(?:e|ed|ing|ion)\b"
    r"|\border\s+(?:was\s+)?(?:placed|filled|completed)\b"
    r"|\b(?:trade|sale|purchase)\s+(?:was\s+)?"
    r"(?:completed|executed|filled)\b"
    r"|(?:giao dịch|lệnh|lệnh bán|lệnh mua).{0,30}"
    r"(?:đã\s+)?(?:được\s+)?(?:thực hiện|đặt|khớp|hoàn (?:tất|thành))"
    r"|(?:cần|yêu cầu).{0,20}phê duyệt"
    r"|an toàn.{0,20}đề xuất",
    flags=re.IGNORECASE | re.DOTALL,
)


def create_analysis_reporter_agent(settings: Settings) -> Agent:
    """Create the tool-free LLM that explains an authoritative analysis."""
    set_tracing_disabled(True)
    return Agent(
        name="Sentinel Analysis Reporter",
        model=settings.agents_model,
        model_settings=build_agent_model_settings(settings),
        instructions=ANALYSIS_REPORTER_INSTRUCTIONS,
        tools=[],
    )


def build_reporter_input(
    message: str,
    analysis: PortfolioAnalysis,
) -> str:
    normalized_message = message.strip()
    if not normalized_message:
        raise ValueError("Analysis request message must not be empty.")

    return (
        "Original user request:\n"
        f"{normalized_message}\n\n"
        "Validated deterministic portfolio analysis:\n"
        f"{analysis.model_dump_json()}"
    )


class AgentAnalysisReporter:
    """Use an LLM to communicate results without giving it safety authority."""

    def __init__(
        self,
        settings: Settings,
        run_agent: RunAgent | None = None,
    ) -> None:
        self._agent = create_analysis_reporter_agent(settings)
        self._run_agent = run_agent or Runner.run

    async def report(
        self,
        message: str,
        analysis: PortfolioAnalysis,
    ) -> str:
        result = await self._run_agent(
            self._agent,
            build_reporter_input(message, analysis),
        )
        output = result.final_output
        if not isinstance(output, str):
            raise ModelBehaviorError(
                "Analysis Reporter returned an unexpected output type."
            )
        if _RESERVED_REPORTER_LANGUAGE.search(output):
            raise ModelBehaviorError(
                "Analysis Reporter used reserved risk or execution language."
            )
        return output
