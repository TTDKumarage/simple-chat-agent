# Configuration reference

All configuration is read from the process environment (via `.env` in development, or real environment variables/secrets in production). See [`.env.example`](../.env.example) for a copy-pasteable template.

## General

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Simple Chat Agent` | Shown in the frontend header and returned by `/api/config`. |
| `HOST` | `0.0.0.0` | Bind address for uvicorn when not overridden on the command line. |
| `PORT` | `8000` | Bind port for uvicorn when not overridden on the command line. |
| `LOG_LEVEL` | `info` | Standard Python logging level. |
| `CORS_ALLOW_ORIGINS` | `*` | Comma-separated list of allowed origins for the API. |

## Model selection and behavior

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | One of `openai`, `anthropic`, `mistral`, `gemini`, `custom_openai`, `custom_anthropic`. |
| `LLM_TEMPERATURE` | `0.7` | Passed straight through to the active provider. |
| `LLM_MAX_TOKENS` | `1024` | Maximum tokens generated per response. |
| `LLM_STREAMING` | `true` | Whether the underlying client streams. `/api/chat/stream` works regardless; this mainly affects `/api/chat`'s internal call pattern and provider-side behavior. |
| `SYSTEM_PROMPT` | see `.env.example` | The base system prompt. When a knowledge base is active, retrieved context is appended to this prompt for each request - it is not a replacement for it. |
| `HISTORY_TURNS` | `10` | Number of prior user/assistant exchanges kept per session and replayed as context on each request. |

## Direct providers

Only fill in the block for the provider named in `LLM_PROVIDER`; the others can be left blank.

### OpenAI

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai`. |
| `OPENAI_MODEL` | e.g. `gpt-4o-mini`, `gpt-4o`. |

### Anthropic

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic`. |
| `ANTHROPIC_MODEL` | Any current Anthropic model ID, e.g. `claude-sonnet-4-5`. There is no built-in default - pin the model explicitly rather than relying on the application to guess a safe one, since model availability changes over time. |

### Mistral

| Variable | Description |
|---|---|
| `MISTRAL_API_KEY` | Required when `LLM_PROVIDER=mistral`. |
| `MISTRAL_MODEL` | Defaults to `mistral-large-latest`. |

### Google Gemini

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Required when `LLM_PROVIDER=gemini`. Generate one in [Google AI Studio](https://aistudio.google.com/apikey) (or via a Vertex AI-linked API key, if your org uses that path). |
| `GEMINI_MODEL` | Any current Gemini model ID, e.g. `gemini-2.5-flash` or `gemini-2.5-pro`. No built-in default, same reasoning as `ANTHROPIC_MODEL` above - pin it explicitly. |

## Gateway-proxied providers

These target an OpenAI- or Anthropic-compatible endpoint that is not OpenAI or Anthropic itself - typically an internal LLM gateway. See [`PROVIDERS.md`](PROVIDERS.md#gateway-proxied-providers) for the full setup walkthrough.

### `custom_openai`

| Variable | Description |
|---|---|
| `CUSTOM_OPENAI_API_KEY` | Key/token issued by the gateway. |
| `CUSTOM_OPENAI_BASE_URL` | Full base URL of the gateway's OpenAI-compatible endpoint, e.g. `https://gateway.internal/openai/v1`. |
| `CUSTOM_OPENAI_MODEL` | The model identifier the gateway expects (this may be an alias the gateway maps to a real upstream model, not a raw provider model ID). |
| `CUSTOM_OPENAI_EXTRA_HEADERS` | Optional JSON object of extra headers the gateway requires, e.g. `{"X-Gateway-Client":"simple-chat-agent"}`. |

### `custom_anthropic`

| Variable | Description |
|---|---|
| `CUSTOM_ANTHROPIC_API_KEY` | Key/token issued by the gateway. |
| `CUSTOM_ANTHROPIC_BASE_URL` | Full base URL of the gateway's Anthropic-compatible endpoint. |
| `CUSTOM_ANTHROPIC_MODEL` | The model identifier the gateway expects. |
| `CUSTOM_ANTHROPIC_VERSION` | `anthropic-version` header value; defaults to `2023-06-01`. Only change this if the gateway requires a different pinned API version. |
| `CUSTOM_ANTHROPIC_EXTRA_HEADERS` | Optional JSON object of extra headers, same format as above. |

## Embeddings (only relevant if the knowledge base is enabled)

| Variable | Default | Description |
|---|---|---|
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `custom_openai`. Embeddings are always requested through an OpenAI-compatible embeddings endpoint (this is also what a gateway typically proxies for embeddings). |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Any embeddings model exposed by the chosen provider. |
| `EMBEDDING_DIMENSION` | `1536` | Must match the output dimension of `EMBEDDING_MODEL`. Used when the Pinecone index needs to be created automatically. |
| `EMBEDDING_API_KEY` | (falls back to `OPENAI_API_KEY` / `CUSTOM_OPENAI_API_KEY`) | Set explicitly if embeddings should use a different credential than the chat model. |
| `EMBEDDING_BASE_URL` | (falls back to `CUSTOM_OPENAI_BASE_URL` when `EMBEDDING_PROVIDER=custom_openai`) | Set explicitly if embeddings are served from a different endpoint than chat. |

## Pinecone knowledge base

Leave `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` blank to run without a knowledge base - the service will operate as a plain chat agent with no retrieval step.

| Variable | Default | Description |
|---|---|---|
| `PINECONE_API_KEY` | - | Enables RAG when set together with `PINECONE_INDEX_NAME`. |
| `PINECONE_INDEX_NAME` | - | Name of the Pinecone index to query (and create, if missing). |
| `PINECONE_NAMESPACE` | - | Optional namespace within the index. |
| `PINECONE_CLOUD` | `aws` | Cloud provider for a newly created serverless index. Ignored if the index already exists. |
| `PINECONE_REGION` | `us-east-1` | Region for a newly created serverless index. Ignored if the index already exists. |
| `PINECONE_TOP_K` | `4` | Number of chunks retrieved per query. |
| `PINECONE_CREATE_IF_MISSING` | `true` | If `false`, the service raises a clear configuration error instead of creating the index when it doesn't exist. |

See [`KNOWLEDGE_BASE.md`](KNOWLEDGE_BASE.md) for how to get documents into the index in the first place.
