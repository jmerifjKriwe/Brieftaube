# ADR-0002: Lean Python monolith (FastAPI + SQLite + asyncio tasks)

Date: 2026-08-20
Status: accepted

## Context

Brieftaube serves a single-digit number of users with low notification
frequency (source: `docs/concepts/architecture.md`). The original
architecture analysis evaluated and rejected: PostgreSQL (unnecessary
operational surface), Redis/message broker + task queue (no load to justify
it), multi-worker deployment (SQLite tolerates one writer well), and a
Python-based Signal client (no maintainable library; the signal-cli-rest-api
container is the sane boundary).

## Decision

One deployable unit: FastAPI on Python 3.13, single uvicorn worker,
SQLite in WAL mode via SQLAlchemy 2.0 async + Alembic. Background work
(retry/escalation loop every ~10s, MQTT consumer via aiomqtt) runs as
`asyncio.create_task` background tasks inside the same process. The only
sidecar is the ready-made `signal-cli-rest-api` container. Sessions are
signed cookies; password hashing argon2.

## Consequences

- One container + one sidecar to operate; one process to debug.
- No broker topology, no worker fleet, no DB server — backup is copying the
  SQLite file.
- Vertical scale only. If load ever grows beyond SQLite's comfort (many
  concurrent writers), SQLAlchemy keeps a Postgres migration on the table;
  that switch requires a new ADR.
- Background tasks must never block the event loop; the retry/escalation
  logic must remain unit-testable independent of the loop.
