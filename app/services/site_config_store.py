"""Small JSON-file store for the admin-editable parts of each site's chat
widget config (API base path + greeting message).

Deliberately not a database - there are only two sites, changes are made by
one admin at a time, and the whole point is that editing it takes effect on
the next page load with no rebuild or redeploy.
"""
import json
import threading
from pathlib import Path

from app.services.site_registry import SITES, get_site

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "site_config.json"
_lock = threading.Lock()


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


def get_frontend_config(site_type: str) -> dict:
    site = get_site(site_type)
    stored = _read_all().get(site_type, {})
    return {
        "type": site_type,
        "label": site["label"],
        "brand": site["brand"],
        "api_base": stored.get("api_base", ""),
        "greeting": stored.get("greeting") or site["default_greeting"],
        "use_gateway_key": stored.get("use_gateway_key", False),
        "api_key": stored.get("api_key", ""),
    }


def set_frontend_config(
    site_type: str, api_base: str, greeting: str, use_gateway_key: bool = False, api_key: str = ""
) -> dict:
    get_site(site_type)  # raises KeyError if unknown
    with _lock:
        data = _read_all()
        data[site_type] = {
            "api_base": api_base.strip(),
            "greeting": greeting.strip(),
            "use_gateway_key": use_gateway_key,
            "api_key": api_key.strip(),
        }
        _write_all(data)
    return get_frontend_config(site_type)


def all_frontend_configs() -> dict:
    return {site_type: get_frontend_config(site_type) for site_type in SITES}
