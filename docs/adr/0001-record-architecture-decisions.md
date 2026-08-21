# ADR-0001: Record architecture decisions

Date: 2026-08-20
Status: accepted

## Context

Brieftaube is developed iteratively, largely with AI agents contributing
code. Verbal or chat-only reasoning disappears; repo-history archaeology is
expensive. Decisions like "why is there no broker?" or "why server-rendered
instead of an SPA?" need a durable, discoverable home, or they get re-litigated
or accidentally reversed.

## Decision

Architecture-relevant decisions are recorded as Architecture Decision
Records in `docs/adr/`, numbered sequentially, using the template in
`docs/adr/_template.md`. The ADR is written in the same PR that implements
the decision. Decisions of record bind agents and humans alike;
`AGENTS.md` points here.

## Consequences

- Every "why" has a URL; PRs and issues reference ADRs instead of retelling
  context.
- Overriding an accepted ADR requires a new ADR that supersedes it —
  not a silent code change.
- Slight process overhead per architectural decision; accepted in exchange
  for context surviving team and agent turnover.
