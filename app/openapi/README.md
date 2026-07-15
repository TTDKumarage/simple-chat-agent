# OpenAPI spec

`openapi.yaml` is generated directly from the running FastAPI app (its actual routes and Pydantic request/response models) - it is not hand-written, so it can't drift from what the API actually serves. **Do not hand-edit it**; regenerate it instead:

```bash
pip install -r requirements-dev.txt
python -m scripts.export_openapi
```

Run that after adding, removing, or changing any endpoint or schema, and commit the updated file alongside the code change.

## What's in it

Only the real JSON API surface (`/api/health`, `/api/config`, `/api/chat`, `/api/chat/stream`, `/api/reset`) - the static frontend route (`/`) is deliberately excluded (`include_in_schema=False` in `app/main.py`), since it serves an HTML page, not a data API operation a gateway would proxy.

## Uploading to a gateway (e.g. WSO2)

This is what `docs/PROVIDERS.md` describes from the other direction - there, this app is the *client* calling an LLM through a gateway. Here, this app is the *backend* being fronted by a gateway: import `openapi.yaml` as the API definition, point its production/sandbox endpoint at wherever this service is actually deployed, and apply whatever auth/guardrail policy you need on top.

Note it's an **OpenAPI 3.1.0** document (FastAPI's default). Most current gateway tooling accepts 3.1, but if yours specifically requires 3.0.x, say so - downgrading isn't just a version-string edit (3.1 leans on full JSON Schema 2020-12, e.g. the `anyOf: [..., {type: 'null'}]` pattern used for optional fields like `session_id`, which 3.0 expresses differently via `nullable: true`), so it needs an actual converter rather than a manual find-and-replace.

## Regenerating after a change

The generator (`scripts/export_openapi.py`) imports `app.main:app` directly and calls FastAPI's own `.openapi()` - it doesn't need any provider credentials configured (no `.env` required) since building the schema doesn't touch the LLM factory or knowledge base, only route/model metadata.
