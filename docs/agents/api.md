# API conventions

Load this file when touching anything under the HTTP surface: routes,
request/response models, auth, error handling.

## Source of truth

- `docs/concepts/api_spec.yaml` is the **contract**.
- FastAPI generates the live OpenAPI schema from code at `/openapi.json`.
- If code and spec disagree, that is a defect: fix the code **or** change the
  spec in the same PR with a note. Never let them drift silently.

## Layout

- Routers live in `src/brieftaube/api/<domain>.py`, included with the
  `/api/v1` prefix; routes serving the UI stay in `main.py` (or a `web/`
  package once it grows) with `include_in_schema=False`.
- Pydantic models for the API surface live next to their router
  (`schemas` module per domain). DB models never leak into responses.
- Route handlers are thin: parse → call service/function → respond.
  Business logic lives in plain, typed functions that tests can hit without
  HTTP.

## Conventions

- Fully typed signatures; response models declared (`response_model=`) so the
  generated schema stays accurate.
- Errors use `HTTPException` with concise `detail` strings; API error bodies
  are not translated — the UI translates its own messages (see
  `docs/agents/frontend.md`).
- Async handlers by default (`async def`); never block the loop — use async
  clients for I/O (the app is single-worker, blocking stalls everything).
- Status codes: 200 read, 201 create, 303 redirect-after-POST for UI flows,
  204 for delete/acknowledge, 401 unauthenticated, 403 wrong role, 404
  unknown resource, 422 validation.
- Every new endpoint gets integration tests (`tests/integration/`) covering
  the happy path plus the relevant error codes.

## Authentication (per api_spec.yaml)

| Consumer | Mechanism | Applies to |
|---|---|---|
| External senders (e.g. Home Assistant) | `X-API-Key` header | `/api/v1/*` ingestion routes |
| Web UI | signed session cookie | UI routes |

Until the auth implementation lands, keep routes that will require auth
grouped so the dependency can be attached in one place.

## Health & meta

`GET /healthz` stays minimal (no DB round-trip, no auth) — it is the
liveness probe for compose/uptime checks.
