from collections.abc import Awaitable, Callable
from typing import Any

from agents import Agent, ModelBehaviorError, Runner, set_tracing_disabled

from app.agent.prompts import REQUEST_INTERPRETER_INSTRUCTIONS
from app.config import Settings
from app.models.chat import ParsedRequest
from app.models.policy import PortfolioPolicy


RunAgent = Callable[..., Awaitable[Any]]


def create_request_interpreter_agent(settings: Settings) -> Agent:
    """Create the tool-free Agent that interprets chat into typed actions."""
    set_tracing_disabled(True)
    return Agent(
        name="Sentinel Request Interpreter",
        model=settings.agents_model,
        instructions=REQUEST_INTERPRETER_INSTRUCTIONS,
        output_type=ParsedRequest,
    )


def build_interpreter_input(
    message: str,
    current_policy: PortfolioPolicy,
) -> str:
    """Build explicit request context without relying on hidden mutable state."""
    normalized_message = message.strip()
    if not normalized_message:
        raise ValueError("Request message must not be empty.")

    return (
        "Current validated portfolio policy:\n"
        f"{current_policy.model_dump_json()}\n\n"
        "User message:\n"
        f"{normalized_message}"
    )


class AgentRequestInterpreter:
    """Interpret chat through an LLM with one schema-failure retry."""

    def __init__(
        self,
        settings: Settings,
        run_agent: RunAgent | None = None,
    ) -> None:
        self._agent = create_request_interpreter_agent(settings)
        self._run_agent = run_agent or Runner.run

    async def interpret(
        self,
        message: str,
        current_policy: PortfolioPolicy,
    ) -> ParsedRequest:
        interpreter_input = build_interpreter_input(message, current_policy)

        for attempt in range(2):
            try:
                result = await self._run_agent(self._agent, interpreter_input)
                interpreted = result.final_output
                if not isinstance(interpreted, ParsedRequest):
                    raise ModelBehaviorError(
                        "Request interpreter returned an unexpected output type."
                    )
                return interpreted
            except ModelBehaviorError:
                if attempt == 1:
                    raise

        raise RuntimeError("Request interpreter retry loop ended unexpectedly.")
