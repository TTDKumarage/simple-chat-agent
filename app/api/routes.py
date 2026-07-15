import logging
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.core.errors import ConfigurationError
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ConfigResponse,
    HealthResponse,
    ResetRequest,
)
from app.services.chat_service import get_chat_service

logger = logging.getLogger(__name__)
router = APIRouter()

SESSION_ID_HEADER = "X-Session-Id"


def _resolve_session_id(session_id: str | None) -> str:
    """A missing, null, or blank session_id means "start a new conversation" -
    generate one so the caller doesn't have to invent an identifier up front."""
    if session_id and session_id.strip():
        return session_id.strip()
    return str(uuid.uuid4())


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/config", response_model=ConfigResponse)
async def config() -> ConfigResponse:
    """Expose the active (non-secret) configuration so the frontend can
    show which provider/model is serving the conversation."""
    settings = get_settings()
    try:
        model = settings.active_model_name() or "unknown"
    except Exception:  # pragma: no cover - defensive only
        model = "unknown"
    return ConfigResponse(
        app_name=settings.app_name,
        provider=settings.llm_provider.value,
        model=model,
        rag_enabled=settings.rag_enabled,
        streaming=settings.llm_streaming,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    service = get_chat_service()
    session_id = _resolve_session_id(request.session_id)
    try:
        reply = await service.chat(session_id, request.message)
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream provider/network errors
        logger.exception("Chat request failed")
        raise HTTPException(status_code=502, detail=f"Upstream model error: {exc}") from exc
    return ChatResponse(session_id=session_id, reply=reply)


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    service = get_chat_service()
    session_id = _resolve_session_id(request.session_id)

    async def token_stream():
        try:
            async for token in service.stream(session_id, request.message):
                yield token
        except ConfigurationError as exc:
            yield f"\n\n[configuration error: {exc}]"
        except Exception as exc:  # pragma: no cover - upstream provider/network errors
            logger.exception("Streaming chat request failed")
            yield f"\n\n[upstream model error: {exc}]"

    # The body is raw streamed text, so there's nowhere in it to also return
    # a server-generated session_id - it goes in a response header instead.
    # Headers arrive before the body, so callers can read it immediately.
    return StreamingResponse(
        token_stream(), media_type="text/plain", headers={SESSION_ID_HEADER: session_id}
    )


@router.post("/reset")
async def reset(request: ResetRequest) -> dict:
    service = get_chat_service()
    await service.reset_session(request.session_id)
    return {"session_id": request.session_id, "reset": True}
