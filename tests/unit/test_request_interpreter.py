import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from agents import ModelBehaviorError

from app.agent.prompts import REQUEST_INTERPRETER_INSTRUCTIONS
from app.agent.request_interpreter import (
    AgentRequestInterpreter,
    build_interpreter_input,
    create_request_interpreter_agent,
)
from app.config import LLMProvider, Settings
from app.models.chat import ActionType, ParsedRequest, ViewPolicyAction
from app.models.policy import PortfolioPolicy


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-key",
    )


def test_request_interpreter_uses_structured_output_and_configured_model() -> None:
    agent = create_request_interpreter_agent(_settings())

    assert agent.model == "litellm/gemini/gemini-3.5-flash-lite"
    assert agent.output_type is ParsedRequest
    assert agent.tools == []
    assert agent.model_settings.max_tokens == 4096
    assert agent.model_settings.reasoning is None
    assert "GENERAL_CHAT" in REQUEST_INTERPRETER_INSTRUCTIONS
    assert "Never create a numeric threshold" in REQUEST_INTERPRETER_INSTRUCTIONS
    assert "Never invent portfolio or market data" in REQUEST_INTERPRETER_INSTRUCTIONS
    assert "Never create an execution action" in REQUEST_INTERPRETER_INSTRUCTIONS


def test_interpreter_input_contains_message_and_current_policy() -> None:
    interpreter_input = build_interpreter_input(
        "Đổi giới hạn thành 40%.",
        PortfolioPolicy(max_asset_weight=Decimal("0.45")),
    )

    assert "Đổi giới hạn thành 40%." in interpreter_input
    assert '"max_asset_weight":"0.45"' in interpreter_input


def test_blank_interpreter_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        build_interpreter_input("   ", PortfolioPolicy())


def test_interpreter_retries_one_invalid_structured_output() -> None:
    calls = 0

    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ModelBehaviorError("invalid output")
        return SimpleNamespace(
            final_output=ParsedRequest(
                actions=[
                    ViewPolicyAction(type=ActionType.VIEW_POLICY),
                ]
            )
        )

    interpreter = AgentRequestInterpreter(_settings(), run_agent=fake_run)
    result = asyncio.run(
        interpreter.interpret("Cho tôi xem policy.", PortfolioPolicy())
    )

    assert calls == 2
    assert result.actions[0].type is ActionType.VIEW_POLICY
