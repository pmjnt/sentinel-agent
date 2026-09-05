import asyncio
from decimal import Decimal

from app.models.chat import (
    AnalyzePortfolioAction,
    ClarificationAction,
    GeneralChatAction,
    ParsedRequest,
    UpdatePolicyAction,
    ViewPolicyAction,
)
from app.models.policy import PolicyPatch, PortfolioPolicy
from app.services.policy_conversation_service import (
    PolicyConversationResult,
    PolicyConversationService,
    PolicyMessageEvent,
)
from app.sessions import InMemoryPolicySessionStore


class StaticInterpreter:
    def __init__(self, parsed_request: ParsedRequest) -> None:
        self.parsed_request = parsed_request

    async def interpret(
        self,
        message: str,
        current_policy: PortfolioPolicy,
    ) -> ParsedRequest:
        return self.parsed_request


def _handle(
    parsed_request: ParsedRequest,
    store: InMemoryPolicySessionStore | None = None,
) -> PolicyConversationResult:
    service = PolicyConversationService(
        interpreter=StaticInterpreter(parsed_request),
        store=store or InMemoryPolicySessionStore(),
    )
    return asyncio.run(service.handle("session-1", "user message"))


def test_update_returns_natural_language_and_new_policy() -> None:
    result = _handle(
        ParsedRequest(
            actions=[
                UpdatePolicyAction(
                    patch=PolicyPatch(max_asset_weight=Decimal("0.40"))
                )
            ]
        )
    )

    assert "Đã cập nhật policy" in result.message
    assert "40%" in result.message
    assert result.policy.max_asset_weight == Decimal("0.40")
    assert result.analysis_requested is False


def test_view_returns_policy_without_changing_it() -> None:
    store = InMemoryPolicySessionStore()
    store.apply(
        "session-1",
        PolicyPatch(min_stablecoin_weight=Decimal("0.30")),
    )

    result = _handle(
        ParsedRequest(actions=[ViewPolicyAction()]),
        store,
    )

    assert "Policy hiện tại" in result.message
    assert "30%" in result.message
    assert store.get("session-1") == result.policy


def test_clarification_stops_without_changing_policy() -> None:
    store = InMemoryPolicySessionStore()

    result = _handle(
        ParsedRequest(
            actions=[
                ClarificationAction(
                    question="Bạn muốn giới hạn tối đa là bao nhiêu phần trăm?"
                )
            ]
        ),
        store,
    )

    assert result.message == (
        "Bạn muốn giới hạn tối đa là bao nhiêu phần trăm?"
    )
    assert result.policy == PortfolioPolicy()
    assert result.analysis_requested is False


def test_update_then_analyze_applies_update_first() -> None:
    result = _handle(
        ParsedRequest(
            actions=[
                UpdatePolicyAction(
                    patch=PolicyPatch(max_asset_weight=Decimal("0.40"))
                ),
                AnalyzePortfolioAction(focus_symbols=["BTC"]),
            ]
        )
    )

    assert result.policy.max_asset_weight == Decimal("0.40")
    assert result.analysis_requested is True
    assert result.focus_symbols == ["BTC"]


def test_analyze_alone_uses_existing_policy() -> None:
    store = InMemoryPolicySessionStore()
    expected_policy = store.apply(
        "session-1",
        PolicyPatch(block_high_volatility=True),
    )

    result = _handle(
        ParsedRequest(actions=[AnalyzePortfolioAction()]),
        store,
    )

    assert result.policy == expected_policy
    assert result.analysis_requested is True
    assert result.message == ""


def test_analyze_before_update_preserves_the_old_policy_snapshot() -> None:
    store = InMemoryPolicySessionStore()
    old_policy = store.apply(
        "session-1",
        PolicyPatch(max_asset_weight=Decimal("0.50")),
    )

    result = _handle(
        ParsedRequest(
            actions=[
                AnalyzePortfolioAction(focus_symbols=["BTC"]),
                UpdatePolicyAction(
                    patch=PolicyPatch(max_asset_weight=Decimal("0.40"))
                ),
            ]
        ),
        store,
    )

    assert result.events[0].policy == old_policy
    assert result.events[0].focus_symbols == ("BTC",)
    assert "Đã cập nhật policy" in result.events[1].message
    assert result.policy.max_asset_weight == Decimal("0.40")


def test_clarification_anywhere_prevents_all_state_changes() -> None:
    store = InMemoryPolicySessionStore()
    original_policy = store.get("session-1")

    result = _handle(
        ParsedRequest(
            actions=[
                UpdatePolicyAction(
                    patch=PolicyPatch(max_asset_weight=Decimal("0.40"))
                ),
                ClarificationAction(question="Bạn muốn áp dụng 40% cho asset nào?"),
            ]
        ),
        store,
    )

    assert result.message == "Bạn muốn áp dụng 40% cho asset nào?"
    assert result.analysis_requested is False
    assert result.policy == original_policy
    assert store.get("session-1") == original_policy


def test_general_chat_returns_message_without_policy_or_analysis_work() -> None:
    store = InMemoryPolicySessionStore()
    original_policy = store.get("session-1")

    result = _handle(
        ParsedRequest(
            actions=[GeneralChatAction(response="Xin chào! Mình là Sentinel.")]
        ),
        store,
    )

    assert result.message == "Xin chào! Mình là Sentinel."
    assert result.events == (
        PolicyMessageEvent("Xin chào! Mình là Sentinel."),
    )
    assert result.policy == original_policy
    assert store.get("session-1") == original_policy
    assert result.analysis_requested is False
