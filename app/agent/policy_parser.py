from collections.abc import Awaitable, Callable
from typing import Any

from agents import Agent, ModelBehaviorError, Runner, set_tracing_disabled

from app.agent.prompts import POLICY_PARSER_INSTRUCTIONS
from app.config import Settings
from app.models.chat import ParsedRequest
from app.models.policy import PortfolioPolicy


RunAgent = Callable[..., Awaitable[Any]]


def create_policy_parser_agent(settings: Settings) -> Agent:
    """Create the tool-free Agent that parses policy chat into typed actions."""
    set_tracing_disabled(True)
    return Agent(
        name="Sentinel Policy Parser",
        model=settings.agents_model,
        instructions=POLICY_PARSER_INSTRUCTIONS,
        output_type=ParsedRequest,
    )


def build_parser_input(
    message: str,
    current_policy: PortfolioPolicy,
) -> str:
    """Build explicit parser context without relying on hidden mutable state."""
    normalized_message = message.strip()
    if not normalized_message:
        raise ValueError("Policy message must not be empty.")

    return (
        "Current validated portfolio policy:\n"
        f"{current_policy.model_dump_json()}\n\n"
        "User message:\n"
        f"{normalized_message}"
    )


class AgentPolicyParser:
    """Parse policy chat through an LLM with one schema-failure retry."""

    def __init__(
        self,
        settings: Settings,
        run_agent: RunAgent | None = None,
    ) -> None:
        self._agent = create_policy_parser_agent(settings)
        self._run_agent = run_agent or Runner.run

    async def parse(
        self,
        message: str,
        current_policy: PortfolioPolicy,
    ) -> ParsedRequest:
        parser_input = build_parser_input(message, current_policy)

        for attempt in range(2):
            try:
                result = await self._run_agent(self._agent, parser_input)
                parsed = result.final_output
                if not isinstance(parsed, ParsedRequest):
                    raise ModelBehaviorError(
                        "Policy parser returned an unexpected output type."
                    )
                return parsed
            except ModelBehaviorError:
                if attempt == 1:
                    raise

        raise RuntimeError("Policy parser retry loop ended unexpectedly.")
