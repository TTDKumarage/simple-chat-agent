# Knowledge base (Pinecone RAG)

The chat agent can optionally ground its answers in a Pinecone index. This is entirely opt-in - `app/services/knowledge_base.py`'s `get_retriever()` returns `None` unless both `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` are set, and `ChatService` simply skips the retrieval step when there's no retriever.

## Enabling it

```env
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=support-docs
PINECONE_NAMESPACE=          # optional
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_TOP_K=4
PINECONE_CREATE_IF_MISSING=true
```

If the named index doesn't already exist and `PINECONE_CREATE_IF_MISSING` is `true` (the default), the service creates a serverless index on startup using `PINECONE_CLOUD` / `PINECONE_REGION` and a dimension matching `EMBEDDING_DIMENSION`. If you'd rather manage index creation yourself (different pod type, existing index, stricter change control), set `PINECONE_CREATE_IF_MISSING=false` - the service will raise a clear configuration error instead of silently creating something if the index is missing.

## Embeddings

Retrieval and ingestion both need an embeddings model. This is configured independently of the chat model, via `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` (see [`CONFIGURATION.md`](CONFIGURATION.md#embeddings-only-relevant-if-the-knowledge-base-is-enabled)):

- `EMBEDDING_PROVIDER=openai` calls OpenAI's embeddings API directly, reusing `OPENAI_API_KEY` unless `EMBEDDING_API_KEY` is set.
- `EMBEDDING_PROVIDER=custom_openai` calls an OpenAI-compatible embeddings endpoint (e.g. the same gateway used for `custom_openai` chat) via `EMBEDDING_BASE_URL` / `EMBEDDING_API_KEY`, falling back to `CUSTOM_OPENAI_BASE_URL` / `CUSTOM_OPENAI_API_KEY` if not set separately.

**`EMBEDDING_DIMENSION` must match whatever `EMBEDDING_MODEL` actually produces.** `text-embedding-3-small` (the default) is 1536-dimensional. If you change the embedding model, update the dimension to match - a mismatch will surface as a Pinecone error on the first query or upsert, not at startup, since the SDK doesn't validate this ahead of time.

The chat model and the embedding model are configured independently and can be entirely different providers - for example, chatting through `custom_anthropic` while embedding through plain `openai`, since Anthropic doesn't offer an embeddings API.

## Getting documents into the index

This repository does not ship an ingestion pipeline - knowledge bases tend to be source- and format-specific (Confluence exports, PDFs, a docs site, a database dump), so ingestion is left to whatever tooling fits your source material. The important part is producing vectors with `langchain_pinecone.PineconeVectorStore` using the exact same `embedding` configuration the running service uses, so that queries and stored vectors are comparable. A minimal example:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore

from app.config import get_settings
from app.services.knowledge_base import build_embeddings

settings = get_settings()
embeddings = build_embeddings(settings)

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
documents = splitter.create_documents([open("docs/faq.md").read()])

PineconeVectorStore.from_documents(
    documents,
    embedding=embeddings,
    index_name=settings.pinecone_index_name,
    namespace=settings.pinecone_namespace,
)
```

Run that as a one-off script (locally, or as a job in whatever pipeline populates your knowledge sources) whenever the underlying documents change. The running chat service only reads from the index; it never writes to it.

## How retrieval is used

On every chat turn, if a retriever is configured, `ChatService._retrieve_context()` runs a similarity search against the incoming message and joins the top `PINECONE_TOP_K` chunks. That text is appended to `SYSTEM_PROMPT` for that turn only - it is not stored in conversation history, so retrieved context doesn't accumulate across a long conversation. `SYSTEM_PROMPT` should explicitly tell the model how to treat this context (the default prompt already does: ground answers in it, and say so when it doesn't cover the question) - see [`CONFIGURATION.md`](CONFIGURATION.md#model-selection-and-behavior).
