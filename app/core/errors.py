"""Configuration validation helpers shared across service builders."""
import json
from typing import Mapping, Optional


class ConfigurationError(RuntimeError):
    """Raised when required configuration for a selected provider is missing or invalid."""


def require(value: Optional[str], env_var: str) -> str:
    if not value:
        raise ConfigurationError(
            f"Missing required configuration '{env_var}' for the selected provider."
        )
    return value


def parse_headers(raw: Optional[str], env_var: str) -> Optional[Mapping[str, str]]:
    if not raw:
        return None
    try:
        headers = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f'{env_var} must be a JSON object, e.g. \'{{"X-Key":"value"}}\''
        ) from exc
    if not isinstance(headers, dict):
        raise ConfigurationError(f"{env_var} must decode to a JSON object")
    return {str(k): str(v) for k, v in headers.items()}
