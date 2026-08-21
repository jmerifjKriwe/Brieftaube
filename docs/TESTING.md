# Testing

Testing is pytest-only: unit, integration, and browser e2e tests all live in
one runner, one configuration, one command set. Playwright tests are plain
pytest tests marked `e2e`.

## How to run

```bash
just test          # unit + integration (e2e excluded by default)
just test-e2e      # Playwright browser tests (requires `just setup` once)
just test-all      # everything
just coverage      # unit + integration with coverage report (htmlcov/)
```

CI runs the same selection (see `.github/workflows/ci.yml`): lint → typecheck
→ tests → e2e → secret scanning.

## Levels — which test where

| Level | Directory & marker | Scope | Typical use |
|---|---|---|---|
| Unit | `tests/unit/` | One function/class, no I/O, in-memory | i18n catalog integrity, pure logic (retry policy math, routing resolution) |
| Integration | `tests/integration/` | Whole app via `TestClient` (ASGI, in-process) | Routes, auth, template rendering, DB round-trips once models exist |
| E2E | `tests/e2e/` + `@pytest.mark.e2e` | Real browser (Playwright) against a live uvicorn server | User-visible flows: locale switch, login, acknowledge a notification |

Rules of thumb:

- **Default to integration level.** The interesting behavior of this app is
  "request in → state change + HTML/API out", which `TestClient` covers fast
  and deterministically. Reserve unit tests for genuinely pure logic.
- **E2e is a scarce resource.** Only user-visible flows that span multiple
  requests or need a real browser (htmx interactions, cookie/locale behavior,
  accessibility basics). A test that can be an integration test must not be
  an e2e test.
- Every bug fix starts with a **regression test at the lowest level that can
  reproduce it** — it must fail before the fix and pass after.

## Conventions

- Files `test_*.py`, functions `test_*` describing behavior:
  `test_index_renders_german_from_cookie`.
- Fixtures live in the `conftest.py` of their level; shared ones in
  `tests/conftest.py`. Prefer purposeful fixtures over long parametrizations
  when readability wins.
- Async tests run with `pytest-asyncio` in `auto` mode — no need for markers.
- Time-dependent logic: freeze or inject time; never `sleep` in tests (the
  e2e `base_url` fixture's bounded startup wait is the only exception).
- Fully typed test code like production code (annotations may be sparse where
  obvious — per-file lint config allows this).

## Fixtures provided

- `tests/conftest.py`: `test_app` (fresh `FastAPI` via `create_app()`),
  `client` (`TestClient`, runs lifespan).
- `tests/e2e/conftest.py`: `base_url` (session-scoped live server on an
  ephemeral port), plus `page`/`browser` from pytest-playwright.

## I18n is test-enforced

`tests/unit/test_i18n.py` fails the build when:

- a locale in `SUPPORTED_LOCALES` has no catalog,
- catalogs diverge in their key sets,
- a translation is empty,
- placeholder formatting breaks.

Consequence: adding UI text means adding the key to **all** catalogs — the
test tells you immediately when you forget one.

## Database tests (once SQLAlchemy/Alembic land)

See `docs/agents/database.md` for the async engine/session test setup and the
"real SQLite file per test via tmp_path" pattern. Until then this section is
aspirational.

## Coverage

`just coverage` reports branch coverage; CI prints it on every test run.
Coverage is a signal, not a target: 100% on pure logic is cheap and good,
chasing 100% on glue code is waste. New features should not visibly drop
overall coverage; gaps that matter get a comment in the PR, not silence.
