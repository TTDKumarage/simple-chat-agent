"""Static registry of the marketing sites served under /banking and /insurance.

This is the single source of truth for each site's identity (brand, theme,
default namespace) so the admin panel, the dynamic chat-widget config routes,
and the knowledge base ingestion endpoint all agree on what "banking" and
"insurance" mean without duplicating the list in multiple places.
"""
from typing import TypedDict


class SiteInfo(TypedDict):
    label: str
    brand: str
    accent: str
    accent_dark: str
    storage_key: str
    default_greeting: str
    default_namespace: str


SITES: dict[str, SiteInfo] = {
    "banking": {
        "label": "Banking — Silverpine Trust Bank",
        "brand": "Silverpine Trust Bank",
        "accent": "#c9a227",
        "accent_dark": "#0a2540",
        "storage_key": "silverpine-chat-session",
        "default_greeting": (
            "Hi! I'm the Silverpine Trust assistant. Ask me about loans, "
            "credit cards, or your account."
        ),
        "default_namespace": "banking",
    },
    "insurance": {
        "label": "Insurance — Havenwell Assurance Group",
        "brand": "Havenwell Assurance",
        "accent": "#ff6b5b",
        "accent_dark": "#0b3d3a",
        "storage_key": "havenwell-chat-session",
        "default_greeting": (
            "Hi! I'm the Havenwell Assurance assistant. Ask me about life, "
            "health, motor, or home cover."
        ),
        "default_namespace": "insurance",
    },
}


def site_choices() -> list[dict]:
    return [{"value": key, "label": info["label"]} for key, info in SITES.items()]


def get_site(site_type: str) -> SiteInfo:
    if site_type not in SITES:
        raise KeyError(f"Unknown site type '{site_type}'. Expected one of {list(SITES)}.")
    return SITES[site_type]
