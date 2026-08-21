# ADR-0003: Server-rendered Jinja2 + htmx instead of a SPA

Date: 2026-08-20
Status: accepted

## Context

The web UI (notification inbox, channel/subscription management, escalation
preferences) is forms-and-tables over a small dataset for a few users. A
SPA (React/Vue + Vite + npm) was considered and rejected because it would
have doubled the toolchain (second build, second dependency tree, second CI
lane), forced API-first endpoints for internal flows, added client-state
and i18n complexity, and made the largest contributor to this codebase —
AI agents — work across two ecosystems instead of one. UI requirements
(incremental updates, no full page reloads for actions) are fully covered
by htmx with server-rendered fragments.

## Decision

The UI is server-rendered Jinja2 templates with htmx for partial updates,
served by the FastAPI process. No JavaScript build chain, no client-side
routing, no frontend package manager. JavaScript beyond htmx requires
justification in the PR. Interactivity must degrade to plain HTTP.

## Consequences

- One language, one test runner (pytest + Playwright), one CI pipeline.
- i18n stays entirely server-side (locale catalogs + cookie/Accept-Language).
- The UI inherits server rendering limits (no offline, no rich client
  state); acceptable for an ops tool on a home network.
- If a genuinely interactive surface ever appears (e.g. drag-and-drop
  escalation design), revisit with a new ADR — the escape hatch is htmx
  extensions first, an isolated SPA island second.
