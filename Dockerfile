FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY frontend ./frontend

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000
ENV PORT=8000

# Shell form (not exec-form array) so $PORT is actually expanded at container
# start - some hosting platforms assign and inject their own PORT for the
# container to listen on rather than using the EXPOSE'd default, and a
# hardcoded --port here would silently ignore that and cause the platform's
# gateway to connect-refuse against a port nothing is listening on.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/api/health || exit 1

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
