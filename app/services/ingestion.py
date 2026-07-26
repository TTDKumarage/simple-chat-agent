"""Ad-hoc knowledge base ingestion for the admin panel.

Unlike `app.services.knowledge_base`, which builds a single retriever from
the server's own environment configuration, this module takes Pinecone and
embedding parameters supplied directly in an admin request. That lets one
running backend embed documents into whichever Pinecone index/namespace the
admin points it at, without needing separate server processes or env
reloads per knowledge base "type".

Pinecone credentials passed in are used only for the duration of a single
ingestion call and are never written to disk.
"""
from dataclasses import dataclass
from typing import Optional

from app.core.errors import ConfigurationError, require
from app.services.kb_admin import clear_existing_chunks
from app.services.pinecone_connection import PineconeConnection, encode_chunk_id, index_dimension

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".json"}


@dataclass
class IngestParams:
    site_type: str
    pinecone_api_key: str
    pinecone_index_name: str
    pinecone_namespace: str
    pinecone_host: str = ""
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_create_if_missing: bool = True
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    embedding_api_key: Optional[str] = None


def decode_file(filename: str, raw: bytes) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ConfigurationError(
            f"Unsupported file type for '{filename}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigurationError(f"'{filename}' is not valid UTF-8 text.") from exc


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Paragraph-aware sliding-window chunker - no extra dependency needed
    for a feature this small."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(para) <= chunk_size:
            current = para
        else:
            # A single paragraph longer than chunk_size: hard-split with overlap.
            start = 0
            while start < len(para):
                end = start + chunk_size
                chunks.append(para[start:end])
                start = end - overlap
            current = ""

    if current:
        chunks.append(current)

    return chunks or [text.strip()]


def _connection(params: IngestParams) -> PineconeConnection:
    return PineconeConnection(
        pinecone_api_key=params.pinecone_api_key,
        pinecone_index_name=params.pinecone_index_name,
        pinecone_host=params.pinecone_host,
        pinecone_namespace=params.pinecone_namespace,
    )


def _build_embeddings(params: IngestParams, dimensions: Optional[int] = None):
    from langchain_openai import OpenAIEmbeddings

    from app.config import get_settings

    api_key = params.embedding_api_key or get_settings().openai_api_key
    kwargs = {"dimensions": dimensions} if dimensions else {}
    return OpenAIEmbeddings(
        model=params.embedding_model,
        api_key=require(api_key, "embedding API key (or server OPENAI_API_KEY)"),
        **kwargs,
    )


def _ensure_index(params: IngestParams) -> None:
    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=params.pinecone_api_key)
    existing = {idx["name"] for idx in pc.list_indexes()}
    if params.pinecone_index_name in existing:
        return
    if not params.pinecone_create_if_missing:
        raise ConfigurationError(
            f"Pinecone index '{params.pinecone_index_name}' does not exist and "
            "'create if missing' is off."
        )
    pc.create_index(
        name=params.pinecone_index_name,
        dimension=params.embedding_dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud=params.pinecone_cloud, region=params.pinecone_region),
    )


def ingest_files(params: IngestParams, files: list[tuple[str, bytes]]) -> dict:
    from langchain_pinecone import PineconeVectorStore

    if not files:
        raise ConfigurationError("No files provided.")

    require(params.pinecone_api_key, "Pinecone API key")
    if not params.pinecone_index_name and not params.pinecone_host:
        raise ConfigurationError("Provide a Pinecone index name or a Pinecone index host.")

    if not params.pinecone_host:
        # Connecting straight to a host (below) skips this - it's needed for
        # API keys that are scoped to a single index and can't call the
        # management API that resolving an index by name requires.
        _ensure_index(params)

    # Always embed at the index's *actual* dimension rather than trusting the
    # admin-entered one - it only agrees when the index was just created from
    # that same value. An existing index with a different dimension would
    # otherwise fail with a mismatch error from Pinecone after the (wasted)
    # embedding call.
    conn = _connection(params)
    target_dimension = index_dimension(conn)
    embeddings = _build_embeddings(params, dimensions=target_dimension)

    if params.pinecone_host:
        store = PineconeVectorStore(
            host=params.pinecone_host,
            embedding=embeddings,
            namespace=params.pinecone_namespace or None,
            pinecone_api_key=params.pinecone_api_key,
        )
    else:
        store = PineconeVectorStore(
            index_name=params.pinecone_index_name,
            embedding=embeddings,
            namespace=params.pinecone_namespace or None,
            pinecone_api_key=params.pinecone_api_key,
        )

    all_chunks: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []
    per_file: list[dict] = []

    for filename, raw in files:
        text = decode_file(filename, raw)
        chunks = chunk_text(text)
        # Clear any chunks from a prior embed of this same filename first, so
        # re-uploading a shorter version doesn't leave old trailing chunks behind.
        clear_existing_chunks(conn, filename)
        all_chunks.extend(chunks)
        all_metadatas.extend(
            {"source": filename, "type": params.site_type, "chunk": i}
            for i in range(len(chunks))
        )
        all_ids.extend(encode_chunk_id(filename, i) for i in range(len(chunks)))
        per_file.append({"filename": filename, "chunks": len(chunks)})

    store.add_texts(all_chunks, metadatas=all_metadatas, ids=all_ids)

    return {
        "status": "ok",
        "index_name": params.pinecone_index_name or params.pinecone_host,
        "namespace": params.pinecone_namespace or "(default)",
        "files_processed": len(files),
        "chunks_embedded": len(all_chunks),
        "files": per_file,
    }
