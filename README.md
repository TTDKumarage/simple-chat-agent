# Simple Chat Agent

A small, provider-agnostic chat service built on [LangChain](https://python.langchain.com/) and FastAPI. It exists to answer one recurring question cheaply: *"can we swap the model/provider without touching code?"*

Everything that varies between deployments — which LLM provider is behind the chat, which model, whether responses are grounded in a knowledge base, whether the model is called directly or through an internal gateway — is controlled by environment variables. The application code itself never changes.

## Highlights

- **Provider-agnostic by design.** Switch between OpenAI, Anthropic, Mistral, and Gemini with a single environment variable (`LLM_PROVIDER`). No code branches to maintain per provider.
- **Gateway-aware.** Two additional providers, `custom_openai` and `custom_anthropic`, target any endpoint that speaks the OpenAI or Anthropic wire protocol but isn't served by OpenAI or Anthropic directly — the typical case being an internal LLM gateway (WSO2 AI Gateway, or similar) that proxies to an upstream model while applying guardrails, auth, rate limiting, and audit logging.
- **Optional retrieval-augmented generation.** Point the service at a Pinecone index and it will retrieve relevant context for every message and fold it into the prompt. Leave Pinecone unconfigured and it behaves as a plain chat agent.
- **Streaming by default.** Responses stream token-by-token to the browser over a plain HTTP response; the same chat service also exposes a non-streaming call for programmatic use.
- **Containerized.** A production-ready `Dockerfile` and `docker-compose.yml` are included; the whole thing runs as a single stateless container plus your chosen model provider and Pinecone.

## Architecture at a glance

```
Browser (frontend/) ─── HTTP ──▶ FastAPI (app/api)
                                     │
                                     ▼
                             ChatService (app/services/chat_service.py)
                              │                        │
                              ▼                        ▼
                     LLM factory                Knowledge base
              (app/services/llm_factory.py)  (app/services/knowledge_base.py)
                              │                        │
            ┌────────────┼────────────┬────────────┐        ▼
            ▼            ▼            ▼            ▼   Pinecone index
        OpenAI      Anthropic     Mistral       Gemini
            │            │
            ▼            ▼
    Custom OpenAI-   Custom Anthropic-
    compatible          compatible
    gateway             gateway
```

Every provider - direct or gateway-proxied - is instantiated as a standard LangChain `BaseChatModel`. The chat service and the API layer never know or care which one is active; they just call `.ainvoke()` / `.astream()`. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full breakdown.

## Quick start (local, no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set LLM_PROVIDER and the matching API key/model

uvicorn app.main:app --reload
```

Open `http://localhost:8000` for the chat UI, or talk to the API directly:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo", "message": "What can you help me with?"}'
```

## Quick start (Docker)

```bash
cp .env.example .env
# edit .env

docker compose up --build
```

The service listens on `http://localhost:8000` by default (see `docker-compose.yml` to change the mapped port).

## Configuration

The full environment variable reference lives in [`.env.example`](.env.example) and is explained in detail in [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md). The short version:

| Concern | Variable | Notes |
|---|---|---|
| Provider selection | `LLM_PROVIDER` | `openai` \| `anthropic` \| `mistral` \| `gemini` \| `custom_openai` \| `custom_anthropic` |
| Model behavior | `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_STREAMING`, `SYSTEM_PROMPT`, `HISTORY_TURNS` | Applies to whichever provider is active |
| Direct providers | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `MISTRAL_API_KEY` / `GEMINI_API_KEY` + matching `*_MODEL` | Only the block for the active provider needs to be filled in |
| Gateway-proxied providers | `CUSTOM_OPENAI_*` / `CUSTOM_ANTHROPIC_*` | Base URL, API key, model, and optional extra headers for an internal gateway - see [`docs/PROVIDERS.md`](docs/PROVIDERS.md#gateway-proxied-providers) |
| Knowledge base (optional) | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `EMBEDDING_*` | Leave blank to disable RAG entirely - see [`docs/KNOWLEDGE_BASE.md`](docs/KNOWLEDGE_BASE.md) |

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - request flow, module layout, and the reasoning behind the provider abstraction
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) - complete environment variable reference
- [`docs/PROVIDERS.md`](docs/PROVIDERS.md) - setting up each provider, including the gateway-proxied (WSO2 AI Gateway-style) providers
- [`docs/KNOWLEDGE_BASE.md`](docs/KNOWLEDGE_BASE.md) - enabling and populating the Pinecone-backed knowledge base
- [`docs/API.md`](docs/API.md) - REST API reference
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) - Docker, docker-compose, and production notes
- [`postman/`](postman) - a ready-to-import Postman collection for exercising the API without writing curl commands

## Project layout

```
app/
  main.py                    FastAPI app, static frontend mount
  config.py                  Settings + provider/embedding enums (env-driven)
  core/errors.py              Shared configuration-validation helpers
  services/
    llm_factory.py            Builds the active LangChain chat model
    knowledge_base.py          Pinecone embeddings/vector store/retriever
    chat_service.py            Per-session history + retrieval + model call
  api/routes.py               /api/health, /api/config, /api/chat(+stream), /api/reset
  models/schemas.py           Request/response models
frontend/                    Static chat UI (no build step)
docs/                        Deep-dive documentation
postman/                     Postman collection + environment for exercising the API
Dockerfile, docker-compose.yml, .dockerignore
requirements.txt, .env.example
```

## License

See [LICENSE](LICENSE).
