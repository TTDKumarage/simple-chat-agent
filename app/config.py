"""Application configuration.

Every runtime knob is driven by an environment variable so the service can be
retargeted (provider, model, gateway endpoint, knowledge base) purely through
deployment configuration - no code changes and no rebuilds.
"""
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported chat model providers.

    The two CUSTOM_* members exist for endpoints that speak the OpenAI or
    Anthropic wire protocol but are not served by OpenAI/Anthropic directly -
    the primary case being an internal LLM gateway (e.g. WSO2 AI Gateway)
    that proxies requests to an upstream model while applying guardrails,
    rate limiting, auditing, etc. From LangChain's perspective these behave
    exactly like the stock provider classes; only the base URL, API key, and
    optional extra headers differ.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MISTRAL = "mistral"
    GEMINI = "gemini"
    CUSTOM_OPENAI = "custom_openai"
    CUSTOM_ANTHROPIC = "custom_anthropic"


class EmbeddingProvider(str, Enum):
    """Providers usable for the embedding step of the RAG pipeline."""

    OPENAI = "openai"
    CUSTOM_OPENAI = "custom_openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General -----------------------------------------------------
    app_name: str = "Simple Chat Agent"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    cors_allow_origins: str = "*"

    # --- LLM selection -------------------------------------------------
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    llm_streaming: bool = True
    system_prompt: str = (
        "You are a helpful, concise assistant. Answer the user's question "
        "directly. If knowledge base context is provided below, ground your "
        "answer in it and say so when the context doesn't cover the question."
    )
    history_turns: int = 10  # number of user/assistant exchanges kept per session

    # --- OpenAI ----------------------------------------------------------
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None  # rarely needed; escape hatch

    # --- Anthropic ---------------------------------------------------------
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None

    # --- Mistral -----------------------------------------------------------
    mistral_api_key: Optional[str] = None
    mistral_model: str = "mistral-large-latest"

    # --- Google Gemini -------------------------------------------------------
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None

    # --- Custom OpenAI-compatible endpoint (e.g. WSO2 AI Gateway) ----------
    custom_openai_api_key: Optional[str] = None
    custom_openai_base_url: Optional[str] = None
    custom_openai_model: Optional[str] = None
    custom_openai_extra_headers: Optional[str] = None  # JSON object as a string

    # --- Custom Anthropic-compatible endpoint (e.g. WSO2 AI Gateway) -------
    custom_anthropic_api_key: Optional[str] = None
    custom_anthropic_base_url: Optional[str] = None
    custom_anthropic_model: Optional[str] = None
    custom_anthropic_version: str = "2023-06-01"
    custom_anthropic_extra_headers: Optional[str] = None  # JSON object as a string

    # --- Embeddings (used for the knowledge base) ---------------------------
    embedding_provider: EmbeddingProvider = EmbeddingProvider.OPENAI
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_api_key: Optional[str] = None
    embedding_base_url: Optional[str] = None

    # --- Pinecone knowledge base -------------------------------------------
    pinecone_api_key: Optional[str] = None
    pinecone_index_name: Optional[str] = None
    pinecone_namespace: Optional[str] = None
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_top_k: int = 4
    pinecone_create_if_missing: bool = True

    @model_validator(mode="after")
    def _fallback_embedding_key(self) -> "Settings":
        # Embeddings default to reusing the OpenAI key unless a dedicated one
        # is supplied - most deployments only have a single OpenAI credential.
        if self.embedding_provider == EmbeddingProvider.OPENAI and not self.embedding_api_key:
            self.embedding_api_key = self.openai_api_key
        if self.embedding_provider == EmbeddingProvider.CUSTOM_OPENAI and not self.embedding_api_key:
            self.embedding_api_key = self.custom_openai_api_key
        if self.embedding_provider == EmbeddingProvider.CUSTOM_OPENAI and not self.embedding_base_url:
            self.embedding_base_url = self.custom_openai_base_url
        return self

    @property
    def rag_enabled(self) -> bool:
        return bool(self.pinecone_api_key and self.pinecone_index_name)

    def active_model_name(self) -> str:
        """Return the model name that will actually be used for the active provider."""
        return {
            LLMProvider.OPENAI: self.openai_model,
            LLMProvider.ANTHROPIC: self.anthropic_model,
            LLMProvider.MISTRAL: self.mistral_model,
            LLMProvider.GEMINI: self.gemini_model,
            LLMProvider.CUSTOM_OPENAI: self.custom_openai_model,
            LLMProvider.CUSTOM_ANTHROPIC: self.custom_anthropic_model,
        }[self.llm_provider]


@lru_cache
def get_settings() -> Settings:
    return Settings()
