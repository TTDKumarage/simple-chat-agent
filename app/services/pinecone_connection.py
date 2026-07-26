"""Shared Pinecone connection helpers used by both ingestion and the admin
"manage embedded files" list/delete endpoints.

Vector IDs are written as "<url-quoted filename>::<chunk index>" so files can
be listed and deleted by name using only ID operations - Pinecone serverless
indexes don't support delete-by-metadata-filter, only delete-by-id (or
delete-all-in-namespace), so the filename has to be recoverable from the ID
alone. URL-quoting (not slugifying) keeps the round trip exact regardless of
spaces/unicode/punctuation in the original filename.
"""
from dataclasses import dataclass
from urllib.parse import quote, unquote

from app.core.errors import ConfigurationError, require

ID_SEPARATOR = "::"


@dataclass
class PineconeConnection:
    pinecone_api_key: str
    pinecone_index_name: str = ""
    pinecone_host: str = ""
    pinecone_namespace: str = ""


def encode_chunk_id(filename: str, chunk_index: int) -> str:
    return f"{quote(filename, safe='')}{ID_SEPARATOR}{chunk_index}"


def decode_filename(chunk_id: str) -> str:
    prefix = chunk_id.split(ID_SEPARATOR, 1)[0]
    return unquote(prefix)


def id_prefix_for(filename: str) -> str:
    return f"{quote(filename, safe='')}{ID_SEPARATOR}"


def get_index(conn: PineconeConnection):
    from pinecone import Pinecone

    require(conn.pinecone_api_key, "Pinecone API key")
    if not conn.pinecone_index_name and not conn.pinecone_host:
        raise ConfigurationError("Provide a Pinecone index name or a Pinecone index host.")

    pc = Pinecone(api_key=conn.pinecone_api_key)
    if conn.pinecone_host:
        return pc.Index(host=conn.pinecone_host)
    return pc.Index(name=conn.pinecone_index_name)


def index_dimension(conn: PineconeConnection) -> int:
    """The index's actual vector dimension, straight from Pinecone - used so
    the embedding call always matches the index instead of trusting a
    hand-entered "Dimension" field that can drift out of sync."""
    index = get_index(conn)
    stats = index.describe_index_stats()
    return stats.dimension
