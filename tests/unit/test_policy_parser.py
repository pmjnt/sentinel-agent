import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from agents import ModelBehaviorError

from app.agent.policy_parser import (
    AgentPolicyParser,
    build_parser_input,
    create_policy_parser_agent,
)
from app.agent.prompts import POLICY_PARSER_INSTRUCTIONS
from app.config import LLMProvider, Settings
from app.models.chat import ActionType, ParsedRequest, ViewPolicyAction
from app.models.policy import PortfolioPolicy


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-key",
    )


def test_policy_parser_agent_uses_structured_output_and_configured_model() -> None:
    agent = create_policy_parser_agent(_settings())

    assert agent.model == "litellm/gemini/gemini-3.5-flash-lite"
    assert agent.output_type is ParsedRequest
    assert agent.tools == []
    assert "Never create a numeric threshold" in POLICY_PARSER_INSTRUCTIONS
    assert "Never create an execution action" in POLICY_PARSER_INSTRUCTIONS


def test_parser_input_contains_message_and_current_policy() -> None:
    parser_input = build_parser_input(
        "Đổi giới hạn thành 40%.",
        PortfolioPolicy(max_asset_weight=Decimal("0.45")),
    )

    assert "Đổi giới hạn thành 40%." in parser_input
    assert '"max_asset_weight":"0.45"' in parser_input


def test_blank_parser_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        build_parser_input("   ", PortfolioPolicy())


def test_parser_retries_one_invalid_structured_output() -> None:
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

    parser = AgentPolicyParser(_settings(), run_agent=fake_run)
    result = asyncio.run(parser.parse("Cho tôi xem policy.", PortfolioPolicy()))

    assert calls == 2
    assert result.actions[0].type is ActionType.VIEW_POLICY
