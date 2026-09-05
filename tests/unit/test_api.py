from decimal import Decimal

from fastapi.testclient import TestClient

from app.api import create_api
from app.config import LLMProvider, Settings
from app.models.api import (
    ActivityEvent,
    ActivityKind,
    ActivityStatus,
    StructuredSentinelResponse,
    TextDeltaEvent,
)
from app.models.policy import PortfolioPolicy
from app.models.profile import InvestorProfile


class FakeStreamingApplication:
    async def stream_handle(self, session_id: str, message: str):
        assert session_id == "user-1"
        assert message == "Analyze my portfolio."
        activity = ActivityEvent(
            sequence=1,
            kind=ActivityKind.PORTFOLIO_READ,
            status=ActivityStatus.COMPLETED,
            message="Completed portfolio retrieval.",
        )
        yield activity
        yield TextDeltaEvent(text="Assessment: balanced.")
        yield StructuredSentinelResponse(
            session_id=session_id,
            message="Done.",
            policy=PortfolioPolicy(max_asset_weight=Decimal("0.40")),
            profile=InvestorProfile(),
            activity=[activity],
        )


def _settings() -> Settings:
    return Settings(
        llm_provider=LLMProvider.OPENAI,
        llm_model="gpt-5.4-mini",
        openai_api_key="test-key",
    )


def test_chat_endpoint_returns_named_safe_sse_events() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": "user-1",
            "message": "Analyze my portfolio.",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: activity" in response.text
    assert "event: text_delta" in response.text
    assert "event: completed" in response.text
    assert "test-key" not in response.text


def test_config_and_static_ui_are_served() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    config = client.get("/api/config")
    page = client.get("/")

    assert config.json() == {
        "provider": "openai",
        "model": "gpt-5.4-mini",
    }
    assert page.status_code == 200
    assert "Sentinel" in page.text
