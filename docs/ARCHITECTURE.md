# Architecture

## Design goal

The single requirement driving every decision in this codebase: **changing the model provider, the model, or the gateway in front of it should never require a code change.** Everything that varies is an environment variable; the application logic is written once against LangChain's provider-agnostic `BaseChatModel` interface and never imports a provider SDK directly outside of `app/services/llm_factory.py`.

## Request flow

1. The browser (or any HTTP client) posts `{session_id, message}` to `/api/chat` or `/api/chat/stream`.
2. `app/api/routes.py` hands the request to a process-wide `ChatService` singleton.
3. `ChatService` (in `app/services/chat_service.py`):
   - looks up (or creates) the in-memory history for `session_id`,
   - if a knowledge base is configured, retrieves the top-k relevant chunks for the incoming message and folds them into the system prompt,
   - assembles `[SystemMessage, *history, HumanMessage]` and calls the active chat model's `.ainvoke()` (blocking) or `.astream()` (streaming),
   - appends the exchange to the session's history.
4. The reply is returned as JSON (`/api/chat`) or streamed as raw text chunks (`/api/chat/stream`).

Nothing in this flow branches on which provider is active - that decision was already made once, at process startup, when `llm_factory.build_chat_model()` ran.

## Module layout

| Module | Responsibility |
|---|---|
| `app/config.py` | Defines `LLMProvider` and `EmbeddingProvider` enums and the `Settings` object (pydantic-settings) that reads every configuration value from the environment. This is the only place that should ever need a new field when adding configuration. |
| `app/core/errors.py` | `ConfigurationError` plus two small helpers (`require`, `parse_headers`) used by both the LLM factory and the knowledge base builder to fail fast with a clear message when required configuration is missing. |
| `app/services/llm_factory.py` | Maps `LLMProvider` to a LangChain chat model constructor. Each branch is a few lines: pull the relevant settings, validate they're present, construct the LangChain class. `get_chat_model()` caches the instance for the life of the process. |
| `app/services/knowledge_base.py` | Builds the embeddings model and the Pinecone vector store/retriever. Returns `None` from `get_retriever()` when Pinecone isn't configured, which is the mechanism that makes RAG optional. |
| `app/services/chat_service.py` | The only stateful piece: in-memory per-session conversation history, prompt assembly, and the actual calls into the model. |
| `app/api/routes.py` | Thin FastAPI routing layer. No business logic lives here beyond translating HTTP requests/responses. |
| `app/main.py` | Application wiring: CORS, router mounting, static frontend serving. |
| `frontend/` | A dependency-free HTML/CSS/JS chat UI. There's no build step because there's nothing to build - it's a static page that talks to the API over `fetch`. |

## Why LangChain's chat model interface rather than raw provider SDKs

Every provider client LangChain exposes (`ChatOpenAI`, `ChatAnthropic`, `ChatMistralAI`, `ChatGoogleGenerativeAI`) implements the same `BaseChatModel` surface: `.invoke()`, `.ainvoke()`, `.stream()`, `.astream()`, all operating on the same `BaseMessage` types (`SystemMessage`, `HumanMessage`, `AIMessage`). That's what makes the factory pattern in `llm_factory.py` possible - `ChatService` is written once against that interface and is completely unaware that six different code paths might have produced the object it's holding.

## Why the "custom" providers are just parameterized versions of the real ones

`ChatOpenAI` and `ChatAnthropic` both accept a `base_url` (routed to `openai_api_base` / `anthropic_api_url` internally) and `default_headers`. An LLM gateway that speaks either provider's wire protocol - which is exactly what something like WSO2 AI Gateway does when proxying to an upstream OpenAI- or Anthropic-compatible model - is therefore indistinguishable from the real provider as far as the LangChain client is concerned. `custom_openai` and `custom_anthropic` in `LLMProvider` are not separate implementations; they're the same `ChatOpenAI`/`ChatAnthropic` classes constructed with a different `base_url`, a gateway-issued API key, and whatever extra headers the gateway needs (an auth token, a client identifier, a guardrail policy tag, etc.). See [`PROVIDERS.md`](PROVIDERS.md#gateway-proxied-providers) for the operational details.

## State and scaling

Conversation history lives in an in-memory dictionary inside the `ChatService` singleton (`app/services/chat_service.py`). That's a deliberate simplification for a "simple chat agent" - it means:

- History does not survive a process restart.
- History is not shared across replicas if you scale the container horizontally.

If either of those matters for your deployment, replace the `_sessions` dictionary with a LangChain-compatible `BaseChatMessageHistory` backed by Redis, a database, or similar - `ChatService` only touches it through `_get_session()` / `reset_session()`, so the blast radius of that change is small.

The Pinecone-backed knowledge base, by contrast, is external and shared by construction - every replica reads from the same index.
