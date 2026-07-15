# API reference

All endpoints are mounted under `/api`. The frontend is served at `/` and talks to the same API.

A ready-to-import Postman collection covering every endpoint below lives in [`postman/`](../postman) - import `simple-chat-agent.postman_collection.json` plus the accompanying environment file, point `base_url` at your running instance, and send requests using the `session_id` collection variable to hold a conversation. See [`postman/README.md`](../postman/README.md) for details.

## `GET /api/health`

Liveness probe. Always returns `200` once the process is up.

```json
{ "status": "ok" }
```

## `GET /api/config`

Returns the active (non-secret) configuration, used by the frontend to display which provider/model is answering.

```json
{
  "app_name": "Simple Chat Agent",
  "provider": "custom_anthropic",
  "model": "claude-sonnet-4-5",
  "rag_enabled": true,
  "streaming": true
}
```

## `POST /api/chat`

Blocking request/response. Waits for the full model response before returning.

**Request**

```json
{ "session_id": "user-123", "message": "What's our refund policy?" }
```

`session_id` is optional. Send a stable, opaque string (the frontend generates a UUID per browser and persists it in `localStorage`) to control which conversation a message belongs to. **Omit it, or send `null`/an empty string, on the first message of a new conversation** - the server generates one and returns it in the response. Reuse the returned value on every following request to continue that conversation; history is scoped to this value.

```json
{ "message": "What's our refund policy?" }
```

**Response**

```json
{ "session_id": "user-123", "reply": "Based on the knowledge base, refunds are..." }
```

`response.session_id` is always present - either the value you sent, or the one the server generated for you.

Errors:

- `500` - the selected provider is missing required configuration (e.g. `LLM_PROVIDER=anthropic` with no `ANTHROPIC_MODEL` set).
- `502` - the upstream model/provider call itself failed (bad credentials, network error, rate limit, etc.). The response body includes the upstream error message for debugging.

## `POST /api/chat/stream`

Same request body as `/api/chat`, with the same optional `session_id` behavior. Returns a `text/plain` streaming response - the response body is the raw reply text, delivered incrementally as the model generates it. There is no SSE framing or JSON wrapping; read the response body as a stream and append chunks as they arrive.

Since the body is raw text, there's nowhere in it to also return a server-generated `session_id` - it comes back in the **`X-Session-Id` response header** instead, present on every response (echoing what you sent, or the generated value if you omitted it). Headers arrive before the streamed body, so it's available immediately.

```bash
curl -i -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize the last release notes"}'
# -i prints response headers, including X-Session-Id, above the streamed body
```

If the request fails partway through (upstream error after streaming has already started), a human-readable error marker (e.g. `\n\n[upstream model error: ...]`) is appended to the stream rather than the connection being abruptly closed, since an HTTP status code can no longer be changed once the body has started streaming.

## `POST /api/reset`

Clears the in-memory conversation history for a session.

**Request**

```json
{ "session_id": "user-123" }
```

**Response**

```json
{ "session_id": "user-123", "reset": true }
```

This does not affect the knowledge base - it only clears the conversational turn history kept for that session.
