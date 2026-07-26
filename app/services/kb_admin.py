"""List and delete already-embedded files for the admin panel.

Groups vectors by the filename encoded into their ID (see
app.services.pinecone_connection) rather than by metadata, since Pinecone
serverless indexes don't support listing or deleting by metadata filter -
only by ID or delete-all-in-namespace.
"""
from collections import defaultdict

from app.core.errors import ConfigurationError
from app.services.pinecone_connection import (
    PineconeConnection,
    decode_filename,
    get_index,
    id_prefix_for,
)


def list_files(conn: PineconeConnection) -> list[dict]:
    index = get_index(conn)
    counts: dict[str, int] = defaultdict(int)
    for batch in index.list(namespace=conn.pinecone_namespace or None):
        for vector_id in batch:
            counts[decode_filename(vector_id)] += 1
    return [{"filename": name, "chunks": n} for name, n in sorted(counts.items())]


def delete_file(conn: PineconeConnection, filename: str) -> int:
    index = get_index(conn)
    ids_to_delete = _ids_for_file(index, conn, filename)
    if not ids_to_delete:
        raise ConfigurationError(f"No embedded chunks found for '{filename}'.")
    index.delete(ids=ids_to_delete, namespace=conn.pinecone_namespace or None)
    return len(ids_to_delete)


def _ids_for_file(index, conn: PineconeConnection, filename: str) -> list[str]:
    prefix = id_prefix_for(filename)
    ids: list[str] = []
    for batch in index.list(prefix=prefix, namespace=conn.pinecone_namespace or None):
        ids.extend(batch)
    return ids


def clear_existing_chunks(conn: PineconeConnection, filename: str) -> None:
    """Best-effort cleanup before re-embedding a file, so re-uploading a
    shorter version doesn't leave the previous version's trailing chunks
    orphaned. Silently does nothing if the file wasn't embedded before."""
    index = get_index(conn)
    ids = _ids_for_file(index, conn, filename)
    if ids:
        index.delete(ids=ids, namespace=conn.pinecone_namespace or None)
