"""Builds a LangChain chat model from the active provider configuration.

Every branch returns a standard LangChain `BaseChatModel`, so nothing
downstream (the chat service, streaming, message history) needs to know or
care which provider is behind it - that's the entire point of routing model
selection through environment variables instead of provider-specific code
paths.

The two "custom" providers (CUSTOM_OPENAI / CUSTOM_ANTHROPIC) target a
gateway that speaks the OpenAI or Anthropic wire protocol but forwards to
whatever upstream model it's configured with - e.g. WSO2 AI Gateway sitting
in front of a model with request/response guardrails applied. LangChain's
OpenAI and Anthropic client classes already support pointing at an arbitrary
base URL, so a "custom" provider is really just the stock client class with
a different `base_url`, a gateway-issued API key, and (optionally) extra
headers the gateway needs for routing or auth.
"""
from functools import lru_cache
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import LLMProvider, Settings, get_settings
from app.core.errors import ConfigurationError as LLMConfigurationError
from app.core.errors import parse_headers as _parse_headers
from app.core.errors import require as _require


def _common_kwargs(settings: Settings) -> dict[str, Any]:
    return {
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "streaming": settings.llm_streaming,
    }


def _build_openai(settings: Settings) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=_require(settings.openai_model, "OPENAI_MODEL"),
        api_key=_require(settings.openai_api_key, "OPENAI_API_KEY"),
        base_url=settings.openai_base_url,
        **_common_kwargs(settings),
    )


def _build_anthropic(settings: Settings) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=_require(settings.anthropic_model, "ANTHROPIC_MODEL"),
        api_key=_require(settings.anthropic_api_key, "ANTHROPIC_API_KEY"),
        **_common_kwargs(settings),
    )


def _build_mistral(settings: Settings) -> BaseChatModel:
    from langchain_mistralai import ChatMistralAI

    return ChatMistralAI(
        model=_require(settings.mistral_model, "MISTRAL_MODEL"),
        api_key=_require(settings.mistral_api_key, "MISTRAL_API_KEY"),
        **_common_kwargs(settings),
    )


def _build_gemini(settings: Settings) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=_require(settings.gemini_model, "GEMINI_MODEL"),
        api_key=_require(settings.gemini_api_key, "GEMINI_API_KEY"),
        **_common_kwargs(settings),
    )


def _build_custom_openai(settings: Settings) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=_require(settings.custom_openai_model, "CUSTOM_OPENAI_MODEL"),
        api_key=_require(settings.custom_openai_api_key, "CUSTOM_OPENAI_API_KEY"),
        base_url=_require(settings.custom_openai_base_url, "CUSTOM_OPENAI_BASE_URL"),
        default_headers=_parse_headers(
            settings.custom_openai_extra_headers, "CUSTOM_OPENAI_EXTRA_HEADERS"
        ),
        **_common_kwargs(settings),
    )


def _build_custom_anthropic(settings: Settings) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=_require(settings.custom_anthropic_model, "CUSTOM_ANTHROPIC_MODEL"),
        api_key=_require(settings.custom_anthropic_api_key, "CUSTOM_ANTHROPIC_API_KEY"),
        base_url=_require(settings.custom_anthropic_base_url, "CUSTOM_ANTHROPIC_BASE_URL"),
        default_headers=_parse_headers(
            settings.custom_anthropic_extra_headers, "CUSTOM_ANTHROPIC_EXTRA_HEADERS"
        ),
        **_common_kwargs(settings),
    )


_BUILDERS = {
    LLMProvider.OPENAI: _build_openai,
    LLMProvider.ANTHROPIC: _build_anthropic,
    LLMProvider.MISTRAL: _build_mistral,
    LLMProvider.GEMINI: _build_gemini,
    LLMProvider.CUSTOM_OPENAI: _build_custom_openai,
    LLMProvider.CUSTOM_ANTHROPIC: _build_custom_anthropic,
}


def build_chat_model(settings: Optional[Settings] = None) -> BaseChatModel:
    settings = settings or get_settings()
    builder = _BUILDERS.get(settings.llm_provider)
    if builder is None:
        raise LLMConfigurationError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    return builder(settings)


@lru_cache
def get_chat_model() -> BaseChatModel:
    """Process-wide singleton so every request reuses one client/connection pool."""
    return build_chat_model()
