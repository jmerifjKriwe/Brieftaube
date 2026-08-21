# AGENTS.md — Binding rules for AI coding agents

This file binds every AI agent (and is a good read for humans, too).
When instructions conflict, this file wins over general habits;
when this file conflicts with reality, stop and ask.

## What this project is

Brieftaube is a self-hosted notification hub: FastAPI + SQLite (WAL) +
server-rendered Jinja2/htmx UI, single uvicorn worker, asyncio background
tasks (retry/escalation loop, MQTT consumer), signal-cli-rest-api as the only
sidecar. Small user base — the architecture is deliberately boring and lean.
Full background: `docs/concepts/` (translated source material).

**Status: scaffolding phase.** Application features are built against the
concept documents, one vertical slice at a time.

## Language policy (hard)

- Development and documentation language is **English**: code, identifiers,
  comments, commit messages, PRs, issues, docs, ADRs.
- The **UI is multilingual** (currently `en`, `de`). Never hardcode
  user-facing text. Every UI string goes into every catalog under
  `src/brieftaube/locales/*.json` as a `t("key")` lookup. Key parity is test-
  enforced (`tests/unit/test_i18n.py`).
- The documents in `docs/concepts/` are translated source material describing
  the product vision. When code and a concept document disagree, the code
  wins and the document gets a follow-up issue.

## Load context on demand — not upfront

Do not read everything. Read what the task needs:

| When you work on … | Read first |
|---|---|
| API endpoints, auth, error shapes | `docs/agents/api.md` + `docs/concepts/api_spec.yaml` |
| Templates, htmx, CSS, i18n | `docs/agents/frontend.md` + `docs/DESIGN.md` |
| Models, migrations, SQLAlchemy | `docs/agents/database.md` + `docs/concepts/data_model.md` |
| Writing or changing tests | `docs/TESTING.md` |
| Commits, branches, PRs, releases | `docs/COLLABORATION.md` |
| Any architecture decision | `docs/adr/` (check for an existing ADR) |
| Domain requirements | `docs/concepts/requirements.md` |
| Overall architecture | `docs/concepts/architecture.md` |
| Background tasks, retry/escalation | `docs/concepts/architecture.md` sections 3-4 |

## Commands

`just` is the entry point (CI runs the same checks via `uv`):

```
just setup        # one-time: deps, Playwright browser, git hooks
just dev          # dev server on http://127.0.0.1:8000
just fmt          # autofix lint + format
just check        # ruff + pyright + unit/integration tests  (the gate)
just test-e2e     # Playwright browser tests
```

## Hard rules

1. **`just check` passes before every push.** Pre-commit enforces ruff on
   every commit; do not bypass hooks (`--no-verify`) — fix the code instead.
2. **Conventional Commits, always** (`feat:`, `fix:`, `docs:`, `refactor:`,
   `test:`, `chore:`, `ci:`, `perf:`; breaking changes as `!` or
   `BREAKING CHANGE:` footer). Releases and the changelog are generated from
   commit titles via release-please. One logical change per commit.
3. **No direct commits to `main`.** Short-lived feature branch → PR →
   review → squash-merge (see `docs/COLLABORATION.md`).
4. **Tests ship with the change, in the same PR.** A bug fix starts with a
   regression test that fails before the fix. Match the test level to the
   behavior (unit/integration/e2e — see `docs/TESTING.md`); e2e tests are
   sparing and marked `@pytest.mark.e2e`.
5. **Fully typed Python.** No `Any` where a concrete type works, no untyped
   defs; pyright must stay clean. Pathlib over `os.path`; `logging` over
   `print`; no naive datetimes (DTZ).
6. **Respect the architecture.** No new infrastructure (broker, Redis, second
   worker, SPA build chain) without an ADR accepted in a PR. Decisions of
   record: `docs/adr/`.
7. **Dependencies are a last resort.** New runtime dependencies require
   justification in the PR (what it does, why existing deps can't, maintenance
   status). Lockfile changes only via `uv lock`, never hand-edited.
8. **Generated files are read-only for you:** `uv.lock`, `CHANGELOG.md`
   (release-please owns it), `.venv/`.
9. **Keep the map current:** when you add a module or change a convention,
   update the affected `docs/agents/*.md` file in the same PR. Docs drift is
   a defect.
10. **Secrets never enter code, tests, examples or history.** Use
    `BRIEFTAUBE_*` env vars (see `.env.example`); gitleaks runs in CI and
    pre-commit.

## Definition of Done (per PR)

- [ ] `just check` green; `just test-e2e` green when UI is touched
- [ ] New/changed behavior is covered by tests at the right level
- [ ] UI strings present in all locale catalogs, rendered via `t()`
- [ ] Docs and `docs/agents/*` updated; ADR written if architectural
- [ ] Conventional Commit title on the PR; history clean enough to read
- [ ] No unjustified new dependencies; no secrets; no generated-file edits

## Project map

```
src/brieftaube/        application package (app factory, i18n, config)
  templates/           Jinja2 templates (base + pages)
  static/css/          stylesheet(s) with design tokens
  locales/             UI translation catalogs (en.json, de.json)
tests/                 unit/ | integration/ | e2e/ (conftest per level)
docs/                  TESTING, COLLABORATION, DESIGN, agents/, adr/, concepts/
.github/workflows/     ci.yml (lint/type/test/e2e/secrets), release-please.yml
justfile               task runner (mirrors CI)
```
