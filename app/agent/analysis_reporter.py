from collections.abc import Awaitable, Callable
from typing import Any

from agents import Agent, ModelBehaviorError, Runner, set_tracing_disabled

from app.agent.model_settings import build_agent_model_settings
from app.agent.output_safety import validate_qualitative_output
from app.agent.prompts import ANALYSIS_REPORTER_INSTRUCTIONS
from app.config import Settings
from app.models.analysis import PortfolioAnalysis


RunAgent = Callable[..., Awaitable[Any]]

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
        return validate_qualitative_output(output)
