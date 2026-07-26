"""JSON-file store for the admin-editable Pinecone/embedding connection
settings on the Knowledge Base tab, so re-opening the admin panel doesn't
require retyping the API key, index/host, namespace, etc. every time.

Same not-a-database rationale as site_config_store.py. Unlike the ingestion
flow (which never persists credentials), this store exists specifically
because the admin asked to save these settings - they're written to disk in
plaintext, same tradeoff as the frontend gateway API key.
"""
import json
import threading
from pathlib import Path

from app.services.site_registry import get_site

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "kb_config.json"
_lock = threading.Lock()

DEFAULTS = {
    "pinecone_api_key": "",
    "pinecone_index_name": "",
    "pinecone_host": "",
    "pinecone_namespace": "",
    "pinecone_cloud": "aws",
    "pinecone_region": "us-east-1",
    "pinecone_create_if_missing": True,
    "embedding_model": "text-embedding-3-small",
    "embedding_dimension": 1536,
    "embedding_api_key": "",
}


def _read_all() -> dict:
    if not STORE_PATH.exists():
        return {}
    try:
        return json.loads(STORE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_all(data: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2))


def get_kb_config(site_type: str) -> dict:
    get_site(site_type)  # raises KeyError if unknown
    stored = _read_all().get(site_type, {})
    config = {**DEFAULTS, **stored}
    if not config["pinecone_namespace"]:
        config["pinecone_namespace"] = site_type
    config["type"] = site_type
    return config


def set_kb_config(site_type: str, fields: dict) -> dict:
    get_site(site_type)
    with _lock:
        data = _read_all()
        data[site_type] = {**DEFAULTS, **fields}
        _write_all(data)
    return get_kb_config(site_type)


def clear_kb_config(site_type: str) -> dict:
    get_site(site_type)
    with _lock:
        data = _read_all()
        data.pop(site_type, None)
        _write_all(data)
    return get_kb_config(site_type)
