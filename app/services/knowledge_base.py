"""Pinecone-backed knowledge base used for retrieval-augmented generation.

The knowledge base is entirely optional. If PINECONE_API_KEY and
PINECONE_INDEX_NAME aren't both set, `get_retriever()` returns None and the
chat service falls back to plain conversation with no retrieval step -
useful for local development or deployments that don't need RAG.
"""
from functools import lru_cache
from typing import Optional

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

from app.config import EmbeddingProvider, Settings, get_settings
from app.core.errors import ConfigurationError as LLMConfigurationError
from app.core.errors import require as _require


def build_embeddings(settings: Settings) -> Embeddings:
    if settings.embedding_provider == EmbeddingProvider.OPENAI:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=_require(settings.embedding_api_key, "OPENAI_API_KEY or EMBEDDING_API_KEY"),
        )

    if settings.embedding_provider == EmbeddingProvider.CUSTOM_OPENAI:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=_require(settings.embedding_api_key, "EMBEDDING_API_KEY"),
            base_url=_require(settings.embedding_base_url, "EMBEDDING_BASE_URL"),
        )

    raise LLMConfigurationError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider}")


def _ensure_index(settings: Settings) -> None:
    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = {idx["name"] for idx in pc.list_indexes()}
    if settings.pinecone_index_name in existing:
        return
    if not settings.pinecone_create_if_missing:
        raise LLMConfigurationError(
            f"Pinecone index '{settings.pinecone_index_name}' does not exist and "
            "PINECONE_CREATE_IF_MISSING is false."
        )
    pc.create_index(
        name=settings.pinecone_index_name,
        dimension=settings.embedding_dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
    )


def build_vector_store(settings: Settings):
    from langchain_pinecone import PineconeVectorStore

    _ensure_index(settings)
    embeddings = build_embeddings(settings)
    return PineconeVectorStore(
        index_name=settings.pinecone_index_name,
        embedding=embeddings,
        namespace=settings.pinecone_namespace,
        pinecone_api_key=settings.pinecone_api_key,
    )


@lru_cache
def get_retriever() -> Optional[VectorStoreRetriever]:
    settings = get_settings()
    if not settings.rag_enabled:
        return None
    store = build_vector_store(settings)
    return store.as_retriever(search_kwargs={"k": settings.pinecone_top_k})
