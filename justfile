# Brieftaube task runner.
# Docs: https://github.com/casey/just
# Keep the commands in sync with .github/workflows/ci.yml (CI runs raw `uv` commands).

default:
    @just --list

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# One-time bootstrap: dependencies, Playwright browser, git hooks.
setup:
    uv sync
    uv run playwright install chromium
    uv run pre-commit install
    @echo "Done. Copy .env.example to .env and adjust, then run `just dev`."

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

# Run the dev server with auto-reload on http://127.0.0.1:8000
dev:
    uv run uvicorn brieftaube.main:app --reload

# Update locked dependencies.
update:
    uv lock --upgrade && uv sync

# ---------------------------------------------------------------------------
# Quality gates — `just check` must pass before every push.
# ---------------------------------------------------------------------------

# Auto-fix lint issues and reformat.
fmt:
    uv run ruff check --fix src tests
    uv run ruff format src tests

# Lint without fixing (CI parity).
lint:
    uv run ruff check src tests
    uv run ruff format --check src tests

# Static type check.
typecheck:
    uv run pyright

# Unit + integration tests (excludes e2e).
test:
    uv run pytest

# End-to-end browser tests (requires `just setup` once).
test-e2e:
    uv run pytest -m e2e

# Everything, including e2e.
test-all:
    uv run pytest -m "e2e or not e2e"

# Unit + integration tests with coverage report.
coverage:
    uv run pytest --cov --cov-report=term-missing --cov-report=html

# Full local gate: lint + typecheck + test. Run before every push.
check: lint typecheck test
    @echo "All checks passed."

# ---------------------------------------------------------------------------
# Documentation (MkDocs — config in mkdocs.yml at the repo root)
# ---------------------------------------------------------------------------

# Live-preview the docs site on http://127.0.0.1:8001 (8001 avoids the app dev server on 8000).
docs-dev:
    uv run mkdocs serve --dev-addr 127.0.0.1:8001

# Strict docs build — warnings fail the build. Output lands in site/.
docs-build:
    uv run mkdocs build --strict

# ---------------------------------------------------------------------------
# Database (requires Alembic env — see docs/agents/database.md for first-time
# setup; until then these recipes intentionally fail fast.)
# ---------------------------------------------------------------------------

# Apply all pending migrations.
db-upgrade:
    uv run alembic upgrade head

# Create a new autogenerate migration: just db-revision "add user table"
db-revision name:
    uv run alembic revision --autogenerate -m "{{name}}"

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

# Build and start app + signal-cli-rest-api sidecar (see compose.yaml).
docker-up:
    docker compose up --build -d

docker-down:
    docker compose down

docker-logs:
    docker compose logs -f app
