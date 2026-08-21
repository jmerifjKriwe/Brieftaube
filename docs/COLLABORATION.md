# Collaboration

How changes reach `main`, how releases happen, and what applies to AI agents
and humans alike. The binding short form for agents lives in `AGENTS.md`;
this document is the reference.

## Branching & pull requests

- **Trunk-based with review:** short-lived feature branches → PR → squash-merge
  into `main`. No direct commits to `main`, no long-lived dev branches.
- Branch names: `feat/…`, `fix/…`, `docs/…`, `chore/…`, `adr/…` — short,
  kebab-case, issue-referencing where applicable (`fix/42-escalation-loop`).
- One PR = one logical change. If the description needs "and also", split it.
- A PR is ready when its checklist is complete (see
  `.github/PULL_REQUEST_TEMPLATE.md`): checks green, tests shipped, docs
  updated, i18n complete, no unjustified dependencies.
- Reviews focus on correctness, tests, and architecture fit; style is
  delegated to ruff and format discussions are not held in review.
- Commits on a branch should be clean enough to read individually; the squash
  title must be the Conventional Commit title of the change.

## Conventional Commits

Every commit title (and thus every squash-merge PR title) follows
[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>)<!>: <imperative summary, lowercase, no period>
```

| Type | Use | Release effect (release-please) |
|---|---|---|
| `feat` | New user-visible capability | minor bump |
| `fix` | Bug fix | patch bump |
| `perf` | Performance improvement without behavior change | patch bump |
| `refactor` | No behavior change | none |
| `docs` / `test` / `chore` / `ci` / `build` | Everything else | none |
| `feat!` / `fix!` or `BREAKING CHANGE:` footer | Incompatible change | **major** bump |

Examples: `feat(api): accept notifications via MQTT`, `fix(i18n): fall back
to English for missing keys`, `docs: expand e2e guidance`.

Breaking changes also get a `BREAKING CHANGE:` footer paragraph describing
the migration.

## Releases (release-please)

Releases are fully automated from merge commit titles:

1. Every push to `main` updates a running **Release PR**
   (`chore(main): release X.Y.Z`) containing `CHANGELOG.md` + version bumps.
2. Merge features/fixes as usual; the Release PR accumulates them.
3. When a release is due, merge the Release PR. release-please tags
   `vX.Y.Z`, creates the GitHub release, and the changelog is final.
4. Publishing steps (Docker image etc.) will hook into
   `.github/workflows/release-please.yml` behind `release_created`.

Notes:

- `CHANGELOG.md` and the version in `pyproject.toml` are **generated** —
  never edit them by hand.
- The default `GITHUB_TOKEN` is sufficient; events triggered by it (e.g. the
  bot's own Release PR updates) do not start CI workflows. That is expected.

## Automation working for you

| Bot | Job | Your part |
|---|---|---|
| CI (`.github/workflows/ci.yml`) | lint / typecheck / tests / e2e / gitleaks on every PR | keep it green; fix forward, never bypass |
| release-please | Release PR + tags + changelog | merge the Release PR when a version is due |
| Dependabot | weekly updates: Python deps (uv), GitHub Actions, Docker base image | review like normal PRs; batch via grouped updates |

## Working with AI agents

- Agents follow `AGENTS.md` without exception; conflicts are escalated to a
  human rather than "creatively solved".
- Agent-authored commits and PRs are normal Conventional Commits — no emoji,
  no "Generated with …" stories in titles. Co-author trailers are welcome.
- A human reviews and merges every PR. Agents do not merge, push to `main`,
  or manage releases themselves.
- Agents never touch `uv.lock` by hand, never edit generated files, and never
  add dependencies without justification in the PR description.

## Repo hygiene

- Delete branches after merge; issues are closed by the PR that fixes them.
- Secrets and credentials never enter the repo — `BRIEFTAUBE_*` env vars
  only (`.env.example` documents them; gitleaks scans history in CI).
- If a commit went somewhere it shouldn't: stop, tell a maintainer, do not
  rewrite remote history on your own.
