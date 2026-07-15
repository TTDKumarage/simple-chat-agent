# Deployment

## Docker image

The `Dockerfile` builds a single-stage `python:3.11-slim` image, installs `requirements.txt`, copies in `app/` and `frontend/`, and runs as a non-root user (`appuser`, uid 1000). It exposes port `8000` and ships a `HEALTHCHECK` that hits `/api/health`.

```bash
docker build -t simple-chat-agent .
docker run -d --name simple-chat-agent \
  -p 8000:8000 \
  --env-file .env \
  simple-chat-agent
```

## docker-compose

```bash
cp .env.example .env
docker compose up --build
```

`docker-compose.yml` builds the image, maps port 8000, loads `.env`, restarts unless stopped, and wires up the same health check as the Dockerfile. There's no database or cache service to compose alongside it - the only external dependencies are whichever LLM provider/gateway you've configured and (optionally) Pinecone, both of which are reached over the network rather than run as sidecar containers.

## Configuration in production

Don't bake `.env` into the image (it's excluded via `.dockerignore`). Inject configuration through your platform's secret/config mechanism instead:

- **Kubernetes**: a `Secret` for API keys and gateway tokens, a `ConfigMap` for the non-secret values (`LLM_PROVIDER`, model names, `PINECONE_*` non-key settings), both mounted as environment variables on the container.
- **Docker Swarm / plain Docker**: `docker run --env-file` pointed at a file that never gets committed, or individual `-e` flags sourced from your secret manager at deploy time.
- **Managed platforms** (ECS, Cloud Run, App Service, etc.): use the platform's native environment variable / secret injection rather than `--env-file`.

## Scaling

The service is stateless from the request-handling perspective except for in-memory conversation history (see [`ARCHITECTURE.md`](ARCHITECTURE.md#state-and-scaling)). Running multiple replicas behind a load balancer works, but a given `session_id`'s history will only be visible to whichever replica happens to handle that request unless you replace the in-memory store with a shared backend. If you need horizontal scaling with consistent history, that's the one change required before scaling out.

The Pinecone knowledge base needs no such change - it's already external and shared across replicas.

## Health checks

`/api/health` is intentionally cheap (no provider or Pinecone call) so it can be used as both a liveness and a startup probe without adding load or failing due to a transient upstream issue. Use `/api/config` (also cheap - it reads settings, not live provider state) if you want a slightly richer readiness signal that confirms the app initialized with the configuration you expect.

## Logging

`LOG_LEVEL` controls the root logging level (default `info`). The service logs the active provider and RAG status once at startup, and logs a stack trace for any unhandled error in the chat endpoints before returning a `502` to the client - check container logs first when a `502` shows up in an unexpected place.
