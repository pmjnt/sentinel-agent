from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.binance.gateway import BinanceCliGateway
from app.binance.runner import BinanceCliRunner
from app.bootstrap import create_application
from app.config import Settings, load_settings
from app.models.api import (
    ActivityEvent,
    ChatStreamRequest,
    StructuredSentinelResponse,
    TextDeltaEvent,
)


WEB_DIRECTORY = Path(__file__).resolve().parent.parent / "web"


class StreamingApplication(Protocol):
    def stream_handle(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[
        ActivityEvent | TextDeltaEvent | StructuredSentinelResponse
    ]: ...


def create_api(
    application: StreamingApplication,
    settings: Settings,
) -> FastAPI:
    api = FastAPI(title="Sentinel", version="1.0.0")

    @api.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/api/config")
    async def configuration() -> dict[str, str]:
        return {
            "provider": settings.llm_provider.value,
            "model": settings.llm_model,
        }

    @api.post("/api/chat/stream")
    async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
        return StreamingResponse(
            _encode_application_stream(application, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    api.mount(
        "/",
        StaticFiles(directory=str(WEB_DIRECTORY), html=True),
        name="web",
    )
    return api


async def _encode_application_stream(
    application: StreamingApplication,
    request: ChatStreamRequest,
) -> AsyncIterator[str]:
    try:
        async for item in application.stream_handle(
            request.session_id,
            request.message,
        ):
            if isinstance(item, ActivityEvent):
                yield _sse("activity", item)
            elif isinstance(item, TextDeltaEvent):
                yield _sse("text_delta", item)
            elif isinstance(item, StructuredSentinelResponse):
                yield _sse("completed", item)
    except Exception:
        yield _sse_data(
            "error",
            '{"message":"Sentinel could not complete the request."}',
        )


def _sse(event: str, payload: BaseModel) -> str:
    return _sse_data(event, payload.model_dump_json())


def _sse_data(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def create_app() -> FastAPI:
    settings = load_settings()
    runner = BinanceCliRunner(settings)
    gateway = BinanceCliGateway(runner, settings.binance_environment)
    application = create_application(settings, gateway)
    return create_api(application, settings)
