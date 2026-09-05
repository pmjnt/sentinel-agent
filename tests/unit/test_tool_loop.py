import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from agents import ModelBehaviorError

from app.agent.controlled_tools import (
    MAX_MARKET_OBSERVATIONS,
    ToolDataError,
    evaluate_cached_portfolio,
    read_market_data,
    read_portfolio,
    stage_policy_update,
)
from app.agent.tool_loop import (
    SentinelToolLoop,
    build_tool_loop_input,
    create_tool_loop_agent,
)
from app.config import LLMProvider, Settings
from app.models.market import MarketData, Volatility
from app.models.policy import PolicyChange, PolicyField, PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.services.portfolio_service import calculate_portfolio


class FakeGateway:
    async def get_portfolio(self):
        return calculate_portfolio(
            [
                PortfolioAsset(
                    symbol="BTC",
                    amount=Decimal("0.05"),
                    usd_value=Decimal("5500"),
                ),
                PortfolioAsset(
                    symbol="USDT",
                    amount=Decimal("4500"),
                    usd_value=Decimal("4500"),
                ),
            ]
        )

    async def get_market_data(self, symbol: str):
        return MarketData(
            symbol=symbol,
            price=Decimal("110000"),
            change_24h_percent=Decimal("-4.2"),
            volatility=Volatility.HIGH,
            estimated_slippage_percent=Decimal("0.05"),
        )


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="test-key",
    )


def test_tool_loop_agent_exposes_only_controlled_tools() -> None:
    agent = create_tool_loop_agent(_settings())

    assert [tool.name for tool in agent.tools] == [
        "get_portfolio",
        "get_market_data",
        "update_policy",
        "view_policy",
        "evaluate_portfolio_risk",
    ]
    assert agent.output_type is None
    assert agent.model_settings.parallel_tool_calls is False


def test_tool_loop_input_contains_current_validated_policy() -> None:
    value = build_tool_loop_input(
        "Phân tích BTC.",
        PortfolioPolicy(max_asset_weight=Decimal("0.40")),
    )

    assert "Phân tích BTC." in value
    assert '"max_asset_weight":"0.40"' in value


def test_general_chat_returns_text_without_events() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        assert kwargs["context"].working_policy == PortfolioPolicy()
        return SimpleNamespace(final_output=" Xin chào! ")

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "xin chào",
            PortfolioPolicy(),
        )
    )

    assert result.final_text == "Xin chào!"
    assert result.events == ()
    assert result.policy_patches == ()
    assert result.analyses == ()


def test_policy_update_with_weight_word_does_not_require_analysis() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        stage_policy_update(
            kwargs["context"],
            [
                PolicyChange(
                    field=PolicyField.MAX_ASSET_WEIGHT,
                    value=Decimal("0.40"),
                )
            ],
        )
        return SimpleNamespace(final_output="Đã đặt tỷ trọng tối đa là 40%.")

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "Đặt tỷ trọng tối đa là 40%.",
            PortfolioPolicy(),
        )
    )

    assert result.final_policy.max_asset_weight == Decimal("0.40")
    assert len(result.policy_patches) == 1


def test_runner_receives_context_that_collects_tool_observations() -> None:
    async def fake_run(agent: Any, prompt: str, **kwargs: Any):
        context = kwargs["context"]
        await read_portfolio(context)
        await read_market_data(context, "BTCUSDT")
        analysis = evaluate_cached_portfolio(context, ["BTC"])
        assert analysis.portfolio is context.portfolio
        return SimpleNamespace(final_output="BTC concentration deserves attention.")

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "Analyze BTC.",
            PortfolioPolicy(max_asset_weight=Decimal("0.40")),
        )
    )

    assert len(result.analyses) == 1
    assert len(result.events) == 1
    assert result.data_errors == ()


def test_non_text_final_output_is_rejected() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        return SimpleNamespace(final_output={"message": "unsafe"})

    with pytest.raises(ModelBehaviorError, match="text output"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "hello",
                PortfolioPolicy(),
            )
        )


def test_analysis_rejects_reserved_execution_claim() -> None:
    async def fake_run(agent: Any, prompt: str, **kwargs: Any):
        context = kwargs["context"]
        await read_portfolio(context)
        await read_market_data(context, "BTCUSDT")
        evaluate_cached_portfolio(context, ["BTC"])
        return SimpleNamespace(final_output="The BTC order was executed.")

    with pytest.raises(ModelBehaviorError, match="reserved risk or execution"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "Analyze BTC.",
                PortfolioPolicy(max_asset_weight=Decimal("0.40")),
            )
        )


def test_financial_request_cannot_finish_without_deterministic_analysis() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        return SimpleNamespace(final_output="Your BTC exposure is not risky.")

    with pytest.raises(ModelBehaviorError, match="without deterministic analysis"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "Analyze my BTC exposure.",
                PortfolioPolicy(),
            )
        )


def test_agent_cannot_stop_after_reading_financial_data() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        context = kwargs["context"]
        await read_portfolio(context)
        return SimpleNamespace(final_output="Your portfolio looks safe.")

    with pytest.raises(ModelBehaviorError, match="before deterministic evaluation"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "Show my holdings.",
                PortfolioPolicy(),
            )
        )


def test_general_chat_rejects_positive_execution_claim() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        return SimpleNamespace(final_output="Your BTC order was executed.")

    with pytest.raises(ModelBehaviorError, match="reserved risk or execution"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "hello",
                PortfolioPolicy(),
            )
        )


def test_market_scope_limit_fails_closed_before_turn_budget_is_exhausted() -> None:
    context = SimpleNamespace()

    async def fake_run(*args: Any, **kwargs: Any):
        nonlocal context
        context = kwargs["context"]
        await read_portfolio(context)
        result = evaluate_cached_portfolio(
            context,
            [f"ASSET{index}" for index in range(MAX_MARKET_OBSERVATIONS + 1)],
        )
        assert isinstance(result, ToolDataError)
        return SimpleNamespace(final_output="Unable to analyze that many markets.")

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "Analyze these portfolio markets.",
            PortfolioPolicy(),
        )
    )

    assert result.analyses == ()
    assert result.data_errors == ("Market analysis scope exceeds the safe limit.",)
