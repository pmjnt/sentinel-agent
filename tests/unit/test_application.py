import asyncio
from decimal import Decimal

from app.application import SentinelApplication
from app.models.analysis import PortfolioAnalysis
from app.models.chat import GeneralChatAction, ParsedRequest
from app.models.policy import PortfolioPolicy
from app.models.portfolio import Portfolio
from app.models.risk import RiskDecision, RiskReasonCode, RiskStatus
from app.models.trade import PlanStatus, RebalancePlan
from app.services.policy_conversation_service import (
    PolicyConversationResult,
    PolicyConversationService,
    PolicyMessageEvent,
    PortfolioAnalysisEvent,
)
from app.services.portfolio_analysis_service import AnalysisDataError
from app.sessions import InMemoryPolicySessionStore


def _analysis(policy: PortfolioPolicy) -> PortfolioAnalysis:
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
        risk_decision=RiskDecision(
            status=RiskStatus.SAFE_TO_PROPOSE,
            reason_codes=[RiskReasonCode.NO_RESTRICTION_TRIGGERED],
            reasons=["No restriction triggered."],
        ),
    )


class FakeConversation:
    def __init__(self, result: PolicyConversationResult) -> None:
        self.result = result

    async def handle(self, session_id: str, message: str):
        return self.result


class FakeAnalysisService:
    def __init__(
        self,
        result: PortfolioAnalysis | None = None,
        error: AnalysisDataError | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[PortfolioPolicy, list[str]]] = []

    async def analyze(self, policy: PortfolioPolicy, focus_symbols: list[str]):
        self.calls.append((policy, focus_symbols))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class FakeReporter:
    def __init__(self, result: str = "Báo cáo phân tích.") -> None:
        self.result = result
        self.calls: list[tuple[str, PortfolioAnalysis]] = []

    async def report(self, message: str, analysis: PortfolioAnalysis) -> str:
        self.calls.append((message, analysis))
        return self.result


class FailingReporter(FakeReporter):
    async def report(self, message: str, analysis: PortfolioAnalysis) -> str:
        raise RuntimeError("provider unavailable")


class StaticInterpreter:
    async def interpret(
        self,
        message: str,
        current_policy: PortfolioPolicy,
    ) -> ParsedRequest:
        return ParsedRequest(
            actions=[GeneralChatAction(response="Xin chào! Mình là Sentinel.")]
        )


def _conversation_result(
    *,
    message: str,
    policy: PortfolioPolicy | None = None,
    analysis_requested: bool = False,
    focus_symbols: list[str] | None = None,
) -> PolicyConversationResult:
    policy = policy or PortfolioPolicy()
    events = []
    if message:
        events.append(PolicyMessageEvent(message))
    if analysis_requested:
        events.append(
            PortfolioAnalysisEvent(
                policy=policy,
                focus_symbols=tuple(focus_symbols or []),
            )
        )
    return PolicyConversationResult(
        events=tuple(events),
        policy=policy,
    )


def test_update_or_view_only_skips_analysis_and_reporter() -> None:
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    analysis_service = FakeAnalysisService(_analysis(policy))
    reporter = FakeReporter()
    application = SentinelApplication(
        FakeConversation(
            _conversation_result(message="Policy hiện tại...", policy=policy)
        ),
        analysis_service,
        reporter,
    )

    result = asyncio.run(application.handle("user-1", "Xem policy."))

    assert result.message == "Policy hiện tại..."
    assert result.policy == policy
    assert result.analysis is None
    assert result.analyses == ()
    assert analysis_service.calls == []
    assert reporter.calls == []


def test_clarification_skips_downstream_collaborators() -> None:
    analysis_service = FakeAnalysisService()
    reporter = FakeReporter()
    application = SentinelApplication(
        FakeConversation(
            _conversation_result(message="Bạn muốn giới hạn bao nhiêu?")
        ),
        analysis_service,
        reporter,
    )

    result = asyncio.run(application.handle("user-1", "Giảm giới hạn."))

    assert result.message == "Bạn muốn giới hạn bao nhiêu?"
    assert analysis_service.calls == []
    assert reporter.calls == []


def test_general_chat_skips_analysis_and_reporter_end_to_end() -> None:
    analysis_service = FakeAnalysisService()
    reporter = FakeReporter()
    conversation = PolicyConversationService(
        interpreter=StaticInterpreter(),
        store=InMemoryPolicySessionStore(),
    )
    application = SentinelApplication(conversation, analysis_service, reporter)

    result = asyncio.run(application.handle("user-1", "xin chào"))

    assert result.message == "Xin chào! Mình là Sentinel."
    assert result.policy == PortfolioPolicy()
    assert result.analysis is None
    assert analysis_service.calls == []
    assert reporter.calls == []


def test_analysis_calls_deterministic_service_then_reporter() -> None:
    policy = PortfolioPolicy(block_high_volatility=True)
    analysis = _analysis(policy)
    analysis_service = FakeAnalysisService(analysis)
    reporter = FakeReporter("BTC hiện không vi phạm policy.")
    application = SentinelApplication(
        FakeConversation(
            _conversation_result(
                message="",
                policy=policy,
                analysis_requested=True,
                focus_symbols=["BTC"],
            )
        ),
        analysis_service,
        reporter,
    )

    result = asyncio.run(application.handle("user-1", "Phân tích BTC."))

    assert analysis_service.calls == [(policy, ["BTC"])]
    assert reporter.calls == [("Phân tích BTC.", analysis)]
    assert "Risk Engine: SAFE_TO_PROPOSE" in result.message
    assert "Execution: NOT_EXECUTED" in result.message
    assert result.message.endswith("BTC hiện không vi phạm policy.")
    assert result.analysis == analysis


def test_policy_update_precedes_analysis_report() -> None:
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    analysis = _analysis(policy)
    application = SentinelApplication(
        FakeConversation(
            _conversation_result(
                message="Đã cập nhật policy: tối đa 40%.",
                policy=policy,
                analysis_requested=True,
            )
        ),
        FakeAnalysisService(analysis),
        FakeReporter("Kết quả phân tích."),
    )

    result = asyncio.run(
        application.handle("user-1", "Đổi thành 40% rồi phân tích.")
    )

    assert result.message.startswith("Đã cập nhật policy: tối đa 40%.")
    assert "Risk Engine: SAFE_TO_PROPOSE" in result.message
    assert result.message.endswith("Kết quả phân tích.")


def test_data_failure_returns_safe_message_and_keeps_policy_update() -> None:
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    reporter = FakeReporter()
    application = SentinelApplication(
        FakeConversation(
            _conversation_result(
                message="Đã cập nhật policy: tối đa 40%.",
                policy=policy,
                analysis_requested=True,
            )
        ),
        FakeAnalysisService(
            error=AnalysisDataError("private provider diagnostic")
        ),
        reporter,
    )

    result = asyncio.run(application.handle("user-1", "Cập nhật và phân tích."))

    assert result.message.startswith("Đã cập nhật policy")
    assert "Binance Demo" in result.message
    assert "không thể được xác minh" in result.message
    assert "private provider diagnostic" not in result.message
    assert result.analysis is None
    assert reporter.calls == []


def test_analyze_before_update_uses_old_policy_and_preserves_response_order() -> None:
    old_policy = PortfolioPolicy(max_asset_weight=Decimal("0.50"))
    new_policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    analysis = _analysis(old_policy)
    analysis_service = FakeAnalysisService(analysis)
    application = SentinelApplication(
        FakeConversation(
            PolicyConversationResult(
                events=(
                    PortfolioAnalysisEvent(old_policy, ("BTC",)),
                    PolicyMessageEvent("Đã cập nhật policy: tối đa 40%."),
                ),
                policy=new_policy,
            )
        ),
        analysis_service,
        FakeReporter("Phân tích theo policy cũ."),
    )

    result = asyncio.run(
        application.handle("user-1", "Phân tích trước, sau đó đổi thành 40%.")
    )

    assert analysis_service.calls == [(old_policy, ["BTC"])]
    assert result.message.index("Phân tích theo policy cũ") < result.message.index(
        "Đã cập nhật policy"
    )
    assert result.policy == new_policy


def test_reporter_failure_keeps_authoritative_facts_and_policy_update() -> None:
    policy = PortfolioPolicy(max_asset_weight=Decimal("0.40"))
    analysis = _analysis(policy)
    application = SentinelApplication(
        FakeConversation(
            _conversation_result(
                message="Đã cập nhật policy: tối đa 40%.",
                policy=policy,
                analysis_requested=True,
            )
        ),
        FakeAnalysisService(analysis),
        FailingReporter(),
    )

    result = asyncio.run(application.handle("user-1", "Cập nhật và phân tích."))

    assert "Đã cập nhật policy" in result.message
    assert "Risk Engine: SAFE_TO_PROPOSE" in result.message
    assert "Execution: NOT_EXECUTED" in result.message
    assert "AI interpretation không khả dụng" in result.message


def test_multiple_analysis_events_are_not_collapsed() -> None:
    policy = PortfolioPolicy()
    analysis = _analysis(policy)
    analysis_service = FakeAnalysisService(analysis)
    reporter = FakeReporter("Qualitative interpretation.")
    application = SentinelApplication(
        FakeConversation(
            PolicyConversationResult(
                events=(
                    PortfolioAnalysisEvent(policy, ("BTC",)),
                    PortfolioAnalysisEvent(policy, ("ETH",)),
                ),
                policy=policy,
            )
        ),
        analysis_service,
        reporter,
    )

    result = asyncio.run(application.handle("user-1", "Phân tích BTC rồi ETH."))

    assert analysis_service.calls == [
        (policy, ["BTC"]),
        (policy, ["ETH"]),
    ]
    assert len(reporter.calls) == 2
    assert result.analyses == (analysis, analysis)
