# Providers

`LLM_PROVIDER` selects one of five code paths in `app/services/llm_factory.py`. This document covers what each one expects and, in particular, how to point the agent at an internal LLM gateway instead of a provider's public API.

## Direct providers

These call the provider's public API directly using its official LangChain integration.

### OpenAI (`LLM_PROVIDER=openai`)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Any chat-completion-capable OpenAI model works. Uses `langchain_openai.ChatOpenAI`.

### Anthropic (`LLM_PROVIDER=anthropic`)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5
```

Uses `langchain_anthropic.ChatAnthropic`. There is no hardcoded default model - Anthropic's model lineup changes over time and pinning a specific ID in code would go stale, so `ANTHROPIC_MODEL` is required.

### Mistral (`LLM_PROVIDER=mistral`)

```env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-large-latest
```

Uses `langchain_mistralai.ChatMistralAI`.

### Google Gemini (`LLM_PROVIDER=gemini`)

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
```

Uses `langchain_google_genai.ChatGoogleGenerativeAI`, talking to the Gemini Developer API. Get a key from [Google AI Studio](https://aistudio.google.com/apikey). As with Anthropic, there's no hardcoded default model - set `GEMINI_MODEL` to whatever current Gemini model you have access to (e.g. `gemini-2.5-flash` for lower latency/cost, `gemini-2.5-pro` for the most capable tier).

## Gateway-proxied providers

`custom_openai` and `custom_anthropic` exist for the common enterprise setup where model traffic doesn't go straight to the provider - it goes through an internal AI gateway first. The gateway typically:

- authenticates and authorizes the calling application,
- applies input/output guardrails (PII redaction, content filtering, prompt-injection detection),
- enforces rate limits and quotas,
- logs and audits requests for compliance,
- and finally forwards the (possibly rewritten) request to the actual upstream model.

As long as the gateway exposes an endpoint that mimics the OpenAI or Anthropic chat completions wire format - which products like **WSO2 AI Gateway** are built to do - LangChain's stock `ChatOpenAI` / `ChatAnthropic` clients can talk to it directly. Nothing about the request/response shape changes; only the base URL, credential, and possibly a couple of extra headers do.

### `custom_openai`

```env
LLM_PROVIDER=custom_openai
CUSTOM_OPENAI_API_KEY=<token issued by the gateway>
CUSTOM_OPENAI_BASE_URL=https://ai-gateway.internal.example.com/openai/v1
CUSTOM_OPENAI_MODEL=gpt-4o-mini
CUSTOM_OPENAI_EXTRA_HEADERS={"X-Gateway-Client":"simple-chat-agent"}
```

`CUSTOM_OPENAI_MODEL` is whatever identifier the gateway expects in the `model` field of the request - this is frequently a gateway-defined alias (e.g. `"team-a-default"`) rather than a raw provider model name, since part of the point of a gateway is deciding which upstream model actually serves a given alias.

`CUSTOM_OPENAI_EXTRA_HEADERS` accepts any JSON object and is sent on every request. Use it for whatever the gateway needs beyond the bearer token in `CUSTOM_OPENAI_API_KEY` - a client identifier, a routing/policy tag, a correlation ID prefix, and so on.

### `custom_anthropic`

```env
LLM_PROVIDER=custom_anthropic
CUSTOM_ANTHROPIC_API_KEY=<token issued by the gateway>
CUSTOM_ANTHROPIC_BASE_URL=https://ai-gateway.internal.example.com/anthropic
CUSTOM_ANTHROPIC_MODEL=claude-sonnet-4-5
CUSTOM_ANTHROPIC_VERSION=2023-06-01
CUSTOM_ANTHROPIC_EXTRA_HEADERS={"X-Gateway-Client":"simple-chat-agent"}
```

Same idea, targeting a gateway endpoint that speaks Anthropic's Messages API shape. `CUSTOM_ANTHROPIC_VERSION` maps to the `anthropic-version` header; only change it if the gateway pins a different version than the SDK default.

### Setting this up against WSO2 AI Gateway

The general pattern, regardless of which upstream model WSO2 AI Gateway routes to:

1. In WSO2 AI Gateway, create an API definition that fronts the target LLM (OpenAI or Anthropic-compatible backend) and exposes an OpenAI- or Anthropic-shaped REST interface - this is standard AI Gateway functionality, since its job is to expose a normalized LLM API surface with policy enforcement in front of it.
2. Attach whatever guardrail policies you need at the gateway level - PII detection, jailbreak/prompt-injection detection, content safety, token quota enforcement. This is the main reason to route through a gateway instead of calling the provider directly, and it is entirely transparent to the application: this service just sends chat completion requests and receives chat completion responses.
3. Generate/subscribe for an application key (or OAuth2 token, depending on how the gateway is configured) and put it in `CUSTOM_OPENAI_API_KEY` / `CUSTOM_ANTHROPIC_API_KEY`.
4. Set `CUSTOM_OPENAI_BASE_URL` / `CUSTOM_ANTHROPIC_BASE_URL` to the gateway's invocation URL for that API (including any path prefix WSO2 assigns, e.g. `/openai-chat/1.0.0`).
5. If the gateway requires additional headers beyond the bearer token (a subscription key header, a consumer key, etc.), set them via `*_EXTRA_HEADERS`.
6. Set `LLM_PROVIDER=custom_openai` or `custom_anthropic` accordingly and restart the service.

No code in this repository needs to change for any of the above - it's exactly the same `ChatOpenAI`/`ChatAnthropic` construction used for the direct providers, just pointed somewhere else.

### Switching between a direct provider and its gateway-proxied twin

Because `custom_openai` reuses `ChatOpenAI` and `custom_anthropic` reuses `ChatAnthropic`, moving from "calling OpenAI directly" to "calling OpenAI through the gateway" (or vice versa) is a matter of changing `LLM_PROVIDER` and the corresponding block of environment variables - nothing else about the application changes, including prompt handling, streaming, and history.
