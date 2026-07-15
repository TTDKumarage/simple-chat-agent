# Postman collection

Two files:

- `simple-chat-agent.postman_collection.json` - every endpoint (`/api/health`, `/api/config`, `/api/chat`, `/api/chat/stream`, `/api/reset`), plus a **New Conversation** helper request.
- `simple-chat-agent.postman_environment.json` - just `base_url`, kept separate from the collection so you can point at different targets (local, Docker, a deployed host) without editing the collection itself.

## Import

1. Postman → **Import** → select both JSON files (or drag them in).
2. Select the **Simple Chat Agent - Local** environment from the environment dropdown (top right).
3. Make sure the backend is running (`docker compose up` or `uvicorn app.main:app`) and, if it's not on `http://localhost:8000`, update `base_url` in the environment.

## Using it

You don't need to invent a `session_id` up front - just start chatting:

1. Run **Chat (blocking)**. Its request body sends `session_id` as `{{session_id}}`, which is blank by default - the backend generates one and returns it.
2. That request's test script automatically saves the returned `session_id` into the `session_id` collection variable.
3. Run **Chat (blocking)** again (or **Chat (streaming)**, or **Reset Session**) - they all reuse `{{session_id}}`, which now holds the generated value, so you're continuing the same conversation without copying anything by hand.

Other requests:

- **Health Check** / **Get Active Config** - quick sanity checks; Get Active Config also tells you which provider/model is actually live.
- **Chat (streaming)** - same request/session_id behavior as Chat (blocking), hits `/api/chat/stream` instead. Postman buffers the response and displays it once the stream completes rather than rendering it incrementally, so it looks the same as the blocking endpoint here; it's the same endpoint the web frontend uses for live token-by-token display in a browser. Because the streamed body is raw text, the session_id comes back as the **`X-Session-Id` response header** instead of the JSON body - check the response's Headers tab.
- **Reset Session** - clears history for the current `session_id` without changing it, so you can start over in the same conversation slot.
- **New Conversation (clear session_id)** - clears the `session_id` collection variable (its actual HTTP call is just a harmless health check; the point is the pre-request script). Run this whenever you want the *next* Chat request to start an unrelated, brand-new conversation instead of continuing the current one.

## Starting a new conversation manually

If you'd rather pick your own `session_id` instead of letting the server generate one (e.g. to use a human-readable name), just set the `session_id` collection variable (Collection → Variables tab) to whatever string you want before sending a request - explicit values are always honored as-is.

## Running it from the command line (Newman)

```bash
npm install -g newman
newman run postman/simple-chat-agent.postman_collection.json \
  -e postman/simple-chat-agent.postman_environment.json
```

Useful as a quick smoke test after changing provider configuration or redeploying.
