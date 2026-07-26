import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.admin_routes import router as admin_router
from app.api.routes import router
from app.config import get_settings
from app.services.site_config_store import get_frontend_config
from app.services.site_registry import get_site

settings = get_settings()

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger("simple-chat-agent")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
BANKING_DIR = FRONTEND_DIR / "banking"
INSURANCE_DIR = FRONTEND_DIR / "insurance"
ADMIN_DIR = FRONTEND_DIR / "admin"

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Provider-agnostic LangChain chat backend with optional Pinecone-backed retrieval.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")


def _serve_page(file_path: Path):
    async def _handler() -> FileResponse:
        return FileResponse(file_path)

    return _handler


if BANKING_DIR.exists():
    app.mount("/banking/static", StaticFiles(directory=BANKING_DIR / "static"), name="banking-static")
    for route_path, filename in {
        "/banking": "index.html",
        "/banking/loans": "loans.html",
        "/banking/credit-cards": "credit-cards.html",
        "/banking/about": "about.html",
    }.items():
        app.add_api_route(route_path, _serve_page(BANKING_DIR / filename), methods=["GET"], include_in_schema=False)

if INSURANCE_DIR.exists():
    app.mount("/insurance/static", StaticFiles(directory=INSURANCE_DIR / "static"), name="insurance-static")
    for route_path, filename in {
        "/insurance": "index.html",
        "/insurance/plans": "plans.html",
        "/insurance/about": "about.html",
    }.items():
        app.add_api_route(route_path, _serve_page(INSURANCE_DIR / filename), methods=["GET"], include_in_schema=False)

if ADMIN_DIR.exists():
    app.mount("/admin/static", StaticFiles(directory=ADMIN_DIR / "static"), name="admin-static")

    @app.get("/admin", include_in_schema=False)
    async def admin_index() -> FileResponse:
        return FileResponse(ADMIN_DIR / "index.html")


def _serve_chat_config(site_type: str):
    async def _handler() -> Response:
        site = get_site(site_type)
        cfg = get_frontend_config(site_type)
        # The gateway API key only goes out on the wire (as the X-API-Key
        # header) when the admin has explicitly toggled it on for this site -
        # flipping the checkbox off suppresses the header without discarding
        # the stored key, so re-enabling it doesn't require retyping it.
        api_key = cfg["api_key"] if cfg["use_gateway_key"] else ""
        js = (
            "window.CHAT_WIDGET_CONFIG = {\n"
            f"  apiBase: {json.dumps(cfg['api_base'])},\n"
            f"  apiKey: {json.dumps(api_key)},\n"
            f"  brand: {json.dumps(site['brand'])},\n"
            f"  accent: {json.dumps(site['accent'])},\n"
            f"  accentDark: {json.dumps(site['accent_dark'])},\n"
            f"  storageKey: {json.dumps(site['storage_key'])},\n"
            f"  greeting: {json.dumps(cfg['greeting'])},\n"
            "};\n"
        )
        return Response(content=js, media_type="application/javascript")

    return _handler


# Served dynamically (not as a static file) so admin changes to the API base
# path or greeting message - made via /admin - take effect on the next page
# load, with no rebuild or redeploy of the site.
app.add_api_route(
    "/banking/chat-config.js", _serve_chat_config("banking"), methods=["GET"], include_in_schema=False
)
app.add_api_route(
    "/insurance/chat-config.js", _serve_chat_config("insurance"), methods=["GET"], include_in_schema=False
)


@app.on_event("startup")
async def log_startup_config() -> None:
    logger.info(
        "%s starting with provider=%s rag_enabled=%s",
        settings.app_name,
        settings.llm_provider.value,
        settings.rag_enabled,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
