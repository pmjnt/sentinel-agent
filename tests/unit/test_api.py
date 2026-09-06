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
    async def stream_handle(
        self,
        session_id: str,
        message: str,
        model_route=None,
    ):
        assert session_id == "user-1"
        assert message == "Analyze my portfolio."
        assert model_route.key == "openai/gpt-5.4-mini"
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

    async def approve_plan(self, session_id: str, plan_id: str):
        assert (session_id, plan_id) == ("user-1", "PLAN-ABC123")
        return {"plan_id": plan_id, "status": "EXECUTED"}

    def reject_plan(self, session_id: str, plan_id: str):
        assert (session_id, plan_id) == ("user-1", "PLAN-ABC123")
        return {"plan_id": plan_id, "status": "REJECTED"}


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
            "provider": "openai",
            "model": "gpt-5.4-mini",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: activity" in response.text
    assert "event: text_delta" in response.text
    assert "event: completed" in response.text
    assert "test-key" not in response.text


def test_models_endpoint_returns_enabled_routes_without_keys() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    response = client.get("/api/models")

    assert response.status_code == 200
    assert response.json() == {
        "default": {
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "label": "gpt-5.4-mini",
        },
        "models": [
            {
                "provider": "openai",
                "model": "gpt-5.4-mini",
                "label": "gpt-5.4-mini",
            }
        ],
    }
    assert "test-key" not in response.text


def test_chat_rejects_route_outside_allowlist_before_streaming() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    response = client.post(
        "/api/chat/stream",
        json={
            "session_id": "user-1",
            "message": "Analyze.",
            "provider": "gemini",
            "model": "unknown",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Selected model is not enabled."


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


def test_plan_approval_and_rejection_use_dedicated_endpoints() -> None:
    client = TestClient(create_api(FakeStreamingApplication(), _settings()))

    approved = client.post(
        "/api/plans/PLAN-ABC123/approve",
        json={"session_id": "user-1"},
    )
    rejected = client.post(
        "/api/plans/PLAN-ABC123/reject",
        json={"session_id": "user-1"},
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "EXECUTED"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
