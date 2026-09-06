import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, HTTPException
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
    ModelCatalogResponse,
    ModelOption,
    StructuredSentinelResponse,
    TextDeltaEvent,
    PlanActionRequest,
)
from app.services.execution_service import ExecutionBlockedError
from app.model_catalog import ModelCatalog, ModelRoute


WEB_DIRECTORY = Path(__file__).resolve().parent.parent / "web"
LOGGER = logging.getLogger(__name__)


class StreamingApplication(Protocol):
    def stream_handle(
        self,
        session_id: str,
        message: str,
        model_route: ModelRoute | None = None,
    ) -> AsyncIterator[
        ActivityEvent | TextDeltaEvent | StructuredSentinelResponse
    ]: ...

    async def approve_plan(self, session_id: str, plan_id: str): ...

    def reject_plan(self, session_id: str, plan_id: str): ...


def create_api(
    application: StreamingApplication,
    settings: Settings,
    catalog: ModelCatalog | None = None,
) -> FastAPI:
    api = FastAPI(title="Sentinel", version="1.0.0")
    model_catalog = catalog or ModelCatalog.from_settings(settings)

    @api.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/api/config")
    async def configuration() -> dict[str, str]:
        return {
            "provider": settings.llm_provider.value,
            "model": settings.llm_model,
        }

    @api.get("/api/models", response_model=ModelCatalogResponse)
    async def models() -> ModelCatalogResponse:
        return ModelCatalogResponse(
            default=_model_option(model_catalog.default),
            models=[_model_option(route) for route in model_catalog.routes],
        )

    @api.post("/api/chat/stream")
    async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
        try:
            model_route = model_catalog.resolve(
                request.provider,
                request.model,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail="Selected model is not enabled.",
            ) from error
        return StreamingResponse(
            _encode_application_stream(application, request, model_route),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @api.post("/api/plans/{plan_id}/approve")
    async def approve_plan(plan_id: str, request: PlanActionRequest):
        try:
            return await application.approve_plan(request.session_id, plan_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Plan was not found.") from error
        except (ExecutionBlockedError, RuntimeError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @api.post("/api/plans/{plan_id}/reject")
    async def reject_plan(plan_id: str, request: PlanActionRequest):
        try:
            return application.reject_plan(request.session_id, plan_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Plan was not found.") from error
        except (ExecutionBlockedError, RuntimeError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    api.mount(
        "/",
        StaticFiles(directory=str(WEB_DIRECTORY), html=True),
        name="web",
    )
    return api


async def _encode_application_stream(
    application: StreamingApplication,
    request: ChatStreamRequest,
    model_route: ModelRoute,
) -> AsyncIterator[str]:
    try:
        async for item in application.stream_handle(
            request.session_id,
            request.message,
            model_route=model_route,
        ):
            if isinstance(item, ActivityEvent):
                yield _sse("activity", item)
            elif isinstance(item, TextDeltaEvent):
                yield _sse("text_delta", item)
            elif isinstance(item, StructuredSentinelResponse):
                yield _sse("completed", item)
    except Exception:
        LOGGER.exception(
            "Sentinel stream failed for route %s",
            model_route.key,
        )
        yield _sse_data(
            "error",
            '{"message":"Sentinel could not complete the request."}',
        )


def _sse(event: str, payload: BaseModel) -> str:
    return _sse_data(event, payload.model_dump_json())


def _sse_data(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


def _model_option(route: ModelRoute) -> ModelOption:
    return ModelOption(
        provider=route.provider.value,
        model=route.model,
        label=route.model,
    )


def create_app() -> FastAPI:
    settings = load_settings()
    catalog = ModelCatalog.from_settings(settings)
    runner = BinanceCliRunner(settings)
    gateway = BinanceCliGateway(runner, settings.binance_environment)
    application = create_application(settings, gateway, catalog)
    return create_api(application, settings, catalog)
