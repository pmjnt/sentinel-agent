import pytest
from pydantic import ValidationError

from app.models.api import (
    ActivityEvent,
    ActivityKind,
    ActivityStatus,
    ChatStreamRequest,
    ExecutionStatus,
    StructuredSentinelResponse,
)
from app.models.policy import PortfolioPolicy
from app.models.profile import InvestorProfile


def test_chat_request_normalizes_required_values() -> None:
    request = ChatStreamRequest(
        session_id=" user-1 ",
        message=" hello ",
        provider=" openai ",
        model=" gpt-5.4-mini ",
    )

    assert request.session_id == "user-1"
    assert request.message == "hello"
    assert request.provider == "openai"
    assert request.model == "gpt-5.4-mini"


def test_chat_request_rejects_oversized_input() -> None:
    with pytest.raises(ValidationError):
        ChatStreamRequest(
            session_id="x" * 129,
            message="Analyze.",
            provider="openai",
            model="gpt-5.4-mini",
        )
    with pytest.raises(ValidationError):
        ChatStreamRequest(
            session_id="user-1",
            message="x" * 8001,
            provider="openai",
            model="gpt-5.4-mini",
        )


def test_structured_response_serializes_ui_fields() -> None:
    activity = ActivityEvent(
        sequence=1,
        kind=ActivityKind.PORTFOLIO_READ,
        status=ActivityStatus.COMPLETED,
        message="Portfolio retrieved from Binance Demo.",
    )
    response = StructuredSentinelResponse(
        session_id="user-1",
        message="Done.",
        policy=PortfolioPolicy(),
        profile=InvestorProfile(),
        activity=[activity],
        execution_status=ExecutionStatus.NOT_EXECUTED,
    )

    payload = response.model_dump(mode="json")

    assert payload["activity"][0]["kind"] == "PORTFOLIO_READ"
    assert payload["execution_status"] == "NOT_EXECUTED"
