## Summary

<!-- What changes and why. Reference the issue (`Closes #123`) where applicable. -->

## Checklist

- [ ] Title follows **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`, `perf:`) — required, releases are automated from it
- [ ] `just check` passes locally (ruff + pyright + unit/integration tests); `just test-e2e` for UI changes
- [ ] Tests added or updated — behavior changes ship with tests, bug fixes with a regression test that fails without the fix
- [ ] All user-facing strings added to **every** locale catalog (`src/brieftaube/locales/*.json`) — no hardcoded UI text
- [ ] Documentation updated where conventions or architecture changed (`docs/`, plus an ADR in `docs/adr/` for architectural decisions)
- [ ] No new dependency — or its necessity and supply-chain check justified below
- [ ] Commits are atomic and individually meaningful (they may be squashed on merge)

## Dependency notes (if any)

<!-- New dependency? Why is it needed, what was checked? -->
