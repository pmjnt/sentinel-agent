import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from agents import ModelBehaviorError

from app.agent.analysis_reporter import (
    AgentAnalysisReporter,
    build_reporter_input,
    create_analysis_reporter_agent,
)
from app.agent.prompts import ANALYSIS_REPORTER_INSTRUCTIONS
from app.config import LLMProvider, Settings
from app.models.analysis import PortfolioAnalysis
from app.models.portfolio import Portfolio
from app.models.risk import RiskDecision, RiskReasonCode, RiskStatus
from app.models.trade import PlanStatus, RebalancePlan
from app.models.policy import PortfolioPolicy


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.GEMINI,
        llm_model="gemini-3.5-flash-lite",
        gemini_api_key="test-key",
    )


def _analysis() -> PortfolioAnalysis:
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    decision = RiskDecision(
        status=RiskStatus.SAFE_TO_PROPOSE,
        reason_codes=[RiskReasonCode.NO_RESTRICTION_TRIGGERED],
        reasons=["No configured blocking or approval rule was triggered."],
    )
    return PortfolioAnalysis(
        policy=policy,
        portfolio=Portfolio(assets=[], total_usd_value=Decimal("0")),
        violations=[],
        market_data=[],
        plan=RebalancePlan(
            violations=[],
            actions=[],
            status=PlanStatus.SAFE_TO_PROPOSE,
            explanation="No action required.",
        ),
        risk_decision=decision,
    )


def test_reporter_agent_uses_configured_model_without_tools() -> None:
    agent = create_analysis_reporter_agent(_settings())

    assert agent.model == "litellm/gemini/gemini-3.5-flash-lite"
    assert agent.output_type is None
    assert agent.tools == []
    assert "must not change" in ANALYSIS_REPORTER_INSTRUCTIONS


def test_reporter_input_contains_question_and_validated_analysis() -> None:
    reporter_input = build_reporter_input("Phân tích BTC.", _analysis())

    assert "Phân tích BTC." in reporter_input
    assert '"risk_decision"' in reporter_input
    assert '"SAFE_TO_PROPOSE"' in reporter_input


def test_report_returns_final_text_from_injected_runner() -> None:
    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(final_output="Kết quả đã được giải thích.")

    reporter = AgentAnalysisReporter(_settings(), run_agent=fake_run)

    assert asyncio.run(reporter.report("Phân tích.", _analysis())) == (
        "Kết quả đã được giải thích."
    )


def test_report_rejects_non_text_model_output() -> None:
    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(final_output={"unsafe": True})

    reporter = AgentAnalysisReporter(_settings(), run_agent=fake_run)

    with pytest.raises(ModelBehaviorError, match="unexpected output type"):
        asyncio.run(reporter.report("Phân tích.", _analysis()))


@pytest.mark.parametrize(
    "unsafe_output",
    [
        "Risk status is SAFE_TO_PROPOSE.",
        "This trade requires approval.",
        "The proposal is safe to propose.",
        "The BTC trade was executed.",
        "The order was filled.",
        "The sale completed successfully.",
        "Lệnh đã được thực hiện.",
        "Giao dịch này cần được phê duyệt.",
        "Lệnh bán đã khớp.",
    ],
)
def test_report_rejects_authoritative_status_or_execution_claims(
    unsafe_output: str,
) -> None:
    async def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(final_output=unsafe_output)

    reporter = AgentAnalysisReporter(_settings(), run_agent=fake_run)

    with pytest.raises(ModelBehaviorError, match="reserved risk or execution"):
        asyncio.run(reporter.report("Phân tích.", _analysis()))
