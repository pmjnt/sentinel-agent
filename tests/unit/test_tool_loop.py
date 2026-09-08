import asyncio
from datetime import UTC, datetime
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
from app.model_catalog import ModelCatalog
from app.models.market import MarketData, MarketDataError, Volatility
from app.models.profile import InvestmentObjective, InvestorProfile
from app.models.policy import PolicyChange, PolicyField, PortfolioPolicy
from app.models.portfolio import PortfolioAsset
from app.models.research import (
    CandidateResearch,
    MarketResearchPlan,
    MarketResearchResult,
    MarketScan,
    MarketTicker,
    ResearchPriority,
    ResearchTimeframe,
    TimeframeResearch,
    TrendDirection,
)
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


def _research_candidate(symbol: str) -> MarketTicker:
    return MarketTicker(
        symbol=symbol,
        price="100",
        change_24h_percent="2",
        quote_volume="1000000",
        observed_at=datetime(2026, 9, 7, tzinfo=UTC),
    )


def _finalized_research() -> MarketResearchResult:
    candidates = (_research_candidate("BTCUSDT"), _research_candidate("ETHUSDT"))
    return MarketResearchResult(
        plan=MarketResearchPlan(
            candidate_limit=3,
            timeframes=[ResearchTimeframe.H1],
            lookback_days=1,
            priorities=[ResearchPriority.MOMENTUM],
        ),
        scan=MarketScan(
            candidates=candidates,
            observed_at=datetime(2026, 9, 7, tzinfo=UTC),
        ),
        analyzed_candidates=tuple(
            CandidateResearch(
                candidate=candidate,
                timeframes=(
                    TimeframeResearch(
                        timeframe=ResearchTimeframe.H1,
                        sample_size=24,
                        return_percent="5",
                        trend=TrendDirection.BULLISH,
                        realized_volatility_percent="1.2",
                        max_drawdown_percent="3",
                        volume_change_percent="8",
                    ),
                ),
            )
            for candidate in candidates
        ),
    )


def test_tool_loop_agent_exposes_only_controlled_tools() -> None:
    agent = create_tool_loop_agent(_settings())

    assert [tool.name for tool in agent.tools] == [
        "get_portfolio",
        "get_market_data",
        "update_policy",
        "view_policy",
        "update_investor_profile",
        "view_investor_profile",
        "evaluate_portfolio_risk",
        "propose_trade",
        "set_market_research_plan",
        "scan_top_markets",
        "analyze_market_history",
        "finalize_market_research",
    ]
    assert agent.output_type is None
    assert agent.model_settings.parallel_tool_calls is False


def test_tool_loop_instructions_require_grounded_advice() -> None:
    instructions = create_tool_loop_agent(_settings()).instructions

    assert isinstance(instructions, str)
    assert "Choose a natural response structure" in instructions
    assert "organize your response with localized headings" not in instructions
    assert "Disclose material uncertainty" in instructions
    assert "objective, time horizon, and acceptable loss" in instructions
    assert "ask one concise clarification question" in instructions
    assert "Never expose hidden chain-of-thought" in instructions
    assert "max_trade_usd" in instructions
    assert "max_slippage_percent" in instructions
    assert "allowed_trade_symbols" in instructions
    assert "cannot loosen" in instructions
    assert "Do not call get_market_data for USDT or USDC" in instructions
    assert "2 to 4" in instructions
    assert "do not ask for optional profile fields" in instructions
    assert "calm, direct, and evidence-driven" in instructions
    assert "set_market_research_plan" in instructions
    assert "finalize_market_research" in instructions
    assert "willing to disagree" in instructions


def test_tool_loop_instructions_allow_user_delegated_candidate_selection() -> None:
    instructions = create_tool_loop_agent(_settings()).instructions

    assert isinstance(instructions, str)
    normalized = " ".join(instructions.split())
    assert (
        "When the user explicitly asks you to choose the preferred opportunity "
        "and requests a concrete trade in the same message, your stated preference "
        "satisfies the selection requirement."
        in normalized
    )
    assert (
        "Do not ask the user to select a symbol in that case; choose one from the "
        "finalized research, refresh its market data, re-run deterministic risk "
        "evaluation, and call propose_trade."
        in normalized
    )
    assert (
        "When deterministic risk allows the requested trade, you must call "
        "propose_trade before writing your final response for that turn."
        in normalized
    )


def test_tool_loop_input_contains_current_validated_policy() -> None:
    value = build_tool_loop_input(
        "Phân tích BTC.",
        PortfolioPolicy(max_asset_weight=Decimal("0.40")),
    )

    assert "Phân tích BTC." in value
    assert '"max_asset_weight":"0.40"' in value


def test_tool_loop_input_marks_complete_advice_profile_as_ready() -> None:
    value = build_tool_loop_input(
        "Give me advice.",
        PortfolioPolicy(),
        InvestorProfile(
            objective=InvestmentObjective.GROWTH,
            time_horizon_months=12,
            acceptable_loss_percent=Decimal("20"),
        ),
    )

    assert "Advice profile readiness:\nREADY" in value


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
    assert result.profile_patches == ()
    assert result.final_profile == InvestorProfile()
    assert result.analyses == ()


def test_tool_loop_reuses_filtered_conversation_session_for_same_user() -> None:
    received_sessions = []

    async def fake_run(*args: Any, **kwargs: Any):
        received_sessions.append(kwargs["session"])
        assert kwargs["run_config"].session_input_callback is not None
        return SimpleNamespace(final_output="Continuing our conversation.")

    loop = SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run)

    asyncio.run(loop.run("First message.", PortfolioPolicy(), "user-1"))
    asyncio.run(loop.run("Follow-up.", PortfolioPolicy(), "user-1"))

    assert received_sessions[0] is received_sessions[1]


def test_model_switch_uses_route_agent_and_same_conversation_session() -> None:
    created_models: list[str] = []
    seen_sessions: list[object] = []

    def fake_create_agent(settings: Settings):
        created_models.append(settings.agents_model)
        return SimpleNamespace(model=settings.agents_model)

    async def fake_run(agent: Any, prompt: str, **kwargs: Any):
        seen_sessions.append(kwargs["session"])
        return SimpleNamespace(final_output="Hello.")

    settings = _settings().model_copy(
        update={
            "llm_allowed_models": (
                "openai/gpt-5.4-mini",
                "gemini/gemini-3.5-flash-lite",
            ),
            "gemini_api_key": "gemini-key",
        }
    )
    catalog = ModelCatalog.from_settings(settings)
    loop = SentinelToolLoop(
        settings,
        FakeGateway(),
        catalog=catalog,
        create_agent=fake_create_agent,
        run_agent=fake_run,
    )

    async def run_both() -> None:
        await loop.run(
            "hello",
            PortfolioPolicy(),
            "user-1",
            model_route=catalog.default,
        )
        await loop.run(
            "hello again",
            PortfolioPolicy(),
            "user-1",
            model_route=catalog.resolve(
                "gemini",
                "gemini-3.5-flash-lite",
            ),
        )

    asyncio.run(run_both())

    assert len({id(session) for session in seen_sessions}) == 1
    assert created_models == [
        "litellm/openai/gpt-5.4-mini",
        "litellm/gemini/gemini-3.5-flash-lite",
    ]


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


def test_analysis_suppresses_reserved_execution_claim_but_keeps_facts() -> None:
    async def fake_run(agent: Any, prompt: str, **kwargs: Any):
        context = kwargs["context"]
        await read_portfolio(context)
        await read_market_data(context, "BTCUSDT")
        evaluate_cached_portfolio(context, ["BTC"])
        return SimpleNamespace(final_output="The BTC order was executed.")

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "Analyze BTC.",
            PortfolioPolicy(max_asset_weight=Decimal("0.40")),
        )
    )

    assert len(result.analyses) == 1
    assert result.final_text == ""


def test_analysis_keeps_advice_that_mentions_validated_risk_status() -> None:
    async def fake_run(agent: Any, prompt: str, **kwargs: Any):
        context = kwargs["context"]
        await read_portfolio(context)
        await read_market_data(context, "BTCUSDT")
        evaluate_cached_portfolio(context, ["BTC"])
        return SimpleNamespace(
            final_output=(
                "Risk Engine returned SAFE_TO_PROPOSE. "
                "Recommendation: keep monitoring concentration."
            )
        )

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "Analyze BTC.",
            PortfolioPolicy(max_asset_weight=Decimal("0.40")),
        )
    )

    assert "Recommendation" in result.final_text


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


def test_personalized_investment_advice_requires_deterministic_analysis() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        return SimpleNamespace(final_output="You should buy more growth assets.")

    with pytest.raises(ModelBehaviorError, match="without deterministic analysis"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "Bạn có lời khuyên đầu tư nào cho tài khoản của tôi không?",
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


def test_market_comparison_requires_finalized_research() -> None:
    async def fake_run(*args: Any, **kwargs: Any):
        context = kwargs["context"]
        context.research_plan = MarketResearchPlan(
            candidate_limit=3,
            timeframes=[ResearchTimeframe.H1],
            lookback_days=1,
            priorities=[ResearchPriority.MOMENTUM],
        )
        context.market_scan = MarketScan(
            candidates=(_research_candidate("BTCUSDT"), _research_candidate("ETHUSDT")),
            observed_at=datetime(2026, 9, 7, tzinfo=UTC),
        )
        return SimpleNamespace(final_output="BTC is my preferred option.")

    with pytest.raises(ModelBehaviorError, match="before market research finalization"):
        asyncio.run(
            SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
                "Compare the strongest Binance markets.",
                PortfolioPolicy(),
            )
        )


def test_finalized_market_research_allows_qualitative_judgment() -> None:
    research = _finalized_research()

    async def fake_run(*args: Any, **kwargs: Any):
        kwargs["context"].market_research_results.append(research)
        return SimpleNamespace(final_output="BTC is my preferred option based on momentum.")

    result = asyncio.run(
        SentinelToolLoop(_settings(), FakeGateway(), run_agent=fake_run).run(
            "Compare the strongest Binance markets.",
            PortfolioPolicy(),
        )
    )

    assert result.final_text.startswith("BTC is my preferred option")
    assert result.market_research_results == (research,)


def test_tool_data_error_discards_model_financial_claim_instead_of_failing() -> None:
    class MarketErrorGateway(FakeGateway):
        async def get_market_data(self, symbol: str):
            return MarketDataError(symbol=symbol, error="unavailable")

    async def fake_run(*args: Any, **kwargs: Any):
        context = kwargs["context"]
        await read_portfolio(context)
        await read_market_data(context, "BTCUSDT")
        return SimpleNamespace(final_output="Risk status is BLOCKED.")

    result = asyncio.run(
        SentinelToolLoop(
            _settings(),
            MarketErrorGateway(),
            run_agent=fake_run,
        ).run("Analyze BTC.", PortfolioPolicy())
    )

    assert result.data_errors == (
        "Market data could not be verified for BTCUSDT.",
    )
    assert result.analyses == ()


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
