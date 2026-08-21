# Brieftaube app container.
# Dev dependencies are excluded; the signal-cli sidecar lives in compose.yaml.

FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer caches independently of the code.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

# SQLite database lives on a mounted volume.
RUN mkdir -p /app/data
VOLUME /app/data
ENV BRIEFTAUBE_DATABASE_PATH=/app/data/brieftaube.db

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "brieftaube.main:app", "--host", "0.0.0.0", "--port", "8000"]
