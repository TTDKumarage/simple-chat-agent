import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.errors import ConfigurationError
from app.models.schemas import (
    DeleteFileRequest,
    DeleteFileResponse,
    EmbeddedFileInfo,
    EmbeddedFilesResponse,
    EmbedResponse,
    FrontendConfigResponse,
    FrontendConfigUpdateRequest,
    KBConfigResponse,
    KBConfigUpdateRequest,
    PineconeConnectionRequest,
    SiteTypeInfo,
)
from app.services.ingestion import IngestParams, ingest_files
from app.services.kb_admin import delete_file, list_files
from app.services.kb_config_store import clear_kb_config, get_kb_config, set_kb_config
from app.services.pinecone_connection import PineconeConnection
from app.services.site_config_store import get_frontend_config, set_frontend_config
from app.services.site_registry import site_choices

logger = logging.getLogger(__name__)
router = APIRouter()


def _summarize_upstream_error(exc: Exception) -> str:
    """Pinecone/OpenAI client exceptions stringify to a multi-line dump
    (status, full response headers, body) - fine for logs, unreadable in a
    one-line admin banner. Pull out just the useful parts when we recognize
    the shape, otherwise fall back to str(exc)."""
    status = getattr(exc, "status", None)
    reason = getattr(exc, "reason", None)
    body = getattr(exc, "body", None)
    if status and (reason or body):
        detail = (body or reason or "").strip()
        return f"{type(exc).__name__} {status}: {detail}"
    return str(exc)


@router.get("/site-types", response_model=list[SiteTypeInfo])
async def site_types() -> list[SiteTypeInfo]:
    return [SiteTypeInfo(**choice) for choice in site_choices()]


@router.get("/frontend-config/{site_type}", response_model=FrontendConfigResponse)
async def read_frontend_config(site_type: str) -> FrontendConfigResponse:
    try:
        return FrontendConfigResponse(**get_frontend_config(site_type))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/frontend-config", response_model=FrontendConfigResponse)
async def update_frontend_config(request: FrontendConfigUpdateRequest) -> FrontendConfigResponse:
    try:
        updated = set_frontend_config(
            request.type,
            request.api_base,
            request.greeting,
            request.use_gateway_key,
            request.api_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FrontendConfigResponse(**updated)


@router.get("/kb-config/{site_type}", response_model=KBConfigResponse)
async def read_kb_config(site_type: str) -> KBConfigResponse:
    try:
        return KBConfigResponse(**get_kb_config(site_type))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/kb-config", response_model=KBConfigResponse)
async def update_kb_config(request: KBConfigUpdateRequest) -> KBConfigResponse:
    fields = request.model_dump(exclude={"type"})
    try:
        updated = set_kb_config(request.type, fields)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return KBConfigResponse(**updated)


@router.post("/kb-config/{site_type}/clear", response_model=KBConfigResponse)
async def clear_kb_config_route(site_type: str) -> KBConfigResponse:
    try:
        cleared = clear_kb_config(site_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return KBConfigResponse(**cleared)


@router.post("/embeddings", response_model=EmbedResponse)
async def create_embeddings(
    site_type: str = Form(...),
    pinecone_api_key: str = Form(...),
    pinecone_index_name: str = Form(""),
    pinecone_namespace: str = Form(""),
    pinecone_host: str = Form(""),
    pinecone_cloud: str = Form("aws"),
    pinecone_region: str = Form("us-east-1"),
    pinecone_create_if_missing: bool = Form(True),
    embedding_model: str = Form("text-embedding-3-small"),
    embedding_dimension: int = Form(1536),
    embedding_api_key: str = Form(""),
    files: list[UploadFile] = File(...),
) -> EmbedResponse:
    params = IngestParams(
        site_type=site_type,
        pinecone_api_key=pinecone_api_key,
        pinecone_index_name=pinecone_index_name,
        pinecone_namespace=pinecone_namespace,
        pinecone_host=pinecone_host,
        pinecone_cloud=pinecone_cloud,
        pinecone_region=pinecone_region,
        pinecone_create_if_missing=pinecone_create_if_missing,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        embedding_api_key=embedding_api_key or None,
    )

    file_payloads = [(f.filename or "untitled.txt", await f.read()) for f in files]

    try:
        result = ingest_files(params, file_payloads)
    except ConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream Pinecone/OpenAI errors
        logger.exception("Embedding request failed")
        raise HTTPException(status_code=502, detail=f"Embedding failed: {_summarize_upstream_error(exc)}") from exc

    return EmbedResponse(**result)


def _connection_from(request: PineconeConnectionRequest) -> PineconeConnection:
    return PineconeConnection(
        pinecone_api_key=request.pinecone_api_key,
        pinecone_index_name=request.pinecone_index_name,
        pinecone_host=request.pinecone_host,
        pinecone_namespace=request.pinecone_namespace,
    )


@router.post("/embedded-files", response_model=EmbeddedFilesResponse)
async def get_embedded_files(request: PineconeConnectionRequest) -> EmbeddedFilesResponse:
    try:
        files = list_files(_connection_from(request))
    except ConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream Pinecone errors
        logger.exception("Listing embedded files failed")
        raise HTTPException(status_code=502, detail=f"Listing failed: {_summarize_upstream_error(exc)}") from exc
    return EmbeddedFilesResponse(files=[EmbeddedFileInfo(**f) for f in files])


@router.post("/embedded-files/delete", response_model=DeleteFileResponse)
async def delete_embedded_file(request: DeleteFileRequest) -> DeleteFileResponse:
    try:
        deleted = delete_file(_connection_from(request), request.filename)
    except ConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - upstream Pinecone errors
        logger.exception("Deleting embedded file failed")
        raise HTTPException(status_code=502, detail=f"Delete failed: {_summarize_upstream_error(exc)}") from exc
    return DeleteFileResponse(filename=request.filename, chunks_deleted=deleted)
