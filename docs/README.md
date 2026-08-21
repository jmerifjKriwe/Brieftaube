# Brieftaube documentation

All documentation in this tree is written in **English**. The concept
documents under [`concepts/`](concepts/requirements.md) are the translated source material
for the product vision; they are superseded piece by piece as features are
built.

| Path | Content |
|---|---|
| [`TESTING.md`](TESTING.md) | Test strategy, levels, conventions, CI mapping |
| [`COLLABORATION.md`](COLLABORATION.md) | Branching, commits, PRs, releases, automation |
| [`DESIGN.md`](DESIGN.md) | UI/UX principles, i18n, accessibility, CSS conventions |
| [`agents/`](agents/api.md) | Deep-dive context files, read on demand per task |
| [`adr/`](adr/0001-record-architecture-decisions.md) | Architecture Decision Records |
| [`concepts/`](concepts/requirements.md) | Source material: requirements, architecture, data model, API spec, roadmap |

## Where to start

- **New to the project:** [`concepts/architecture.md`](concepts/architecture.md)
  for the big picture, then this README and [`DESIGN.md`](DESIGN.md).
- **Building a feature:** the matching [`agents/`](agents/api.md) page plus the
  concept document for the domain in question.
- **Deciding something architectural:** read [`adr/`](adr/0001-record-architecture-decisions.md) first — if the
  decision is not recorded yet, write an ADR as part of your PR.

## Conventions for docs

- Markdown, one H1 per file, ATX headings, 80–100 cols where reasonable.
- Prefer tables and short lists over prose walls; link instead of duplicating.
- Docs updates ship in the same PR as the change they describe.

## Documentation site

This tree is also published as an MkDocs site (Material theme); the
configuration lives in `mkdocs.yml` at the repo root. `just docs-dev` serves a
live preview on <http://127.0.0.1:8001>; `just docs-build` runs a strict build
(warnings fail) into `site/`.
