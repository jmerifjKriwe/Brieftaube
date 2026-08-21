# Design

UI/UX principles for Brieftaube's server-rendered interface. Deep-dive
conventions for templates/htmx live in `docs/agents/frontend.md`; this file
is the "why" and the look-and-feel contract.

## Principles

1. **Server-rendered first, htmx for interactivity.** The UI works without
   JavaScript; htmx (`hx-*` attributes) progressively enhances it. No SPA,
   no client-side routing, no build chain (ADR-0002/0003).
2. **Dense, calm, functional.** This is an operations tool used a handful of
   times a day by a few people. Clarity beats delight; there is deliberately
   no marketing surface.
3. **Every string translated.** UI text only via `t("key")` from the locale
   catalogs — never hardcoded, never inline in Python. German and English
   catalogs stay key-parity (test-enforced).
4. **Accessible by default.** WCAG 2.2 AA as target: semantic HTML, real
   buttons/links, visible focus styles, contrast ≥ 4.5:1, `lang` attribute
   tracks the active locale.
5. **Fast and boring.** One stylesheet, no web fonts initially, no animation
   beyond subtle transitions. Pages render in one round-trip.

## Internationalization

- Catalogs: `src/brieftaube/locales/<locale>.json`, flat `key.subkey` maps.
- English is the **source language** (`en.json` is the key set of record);
  `de.json` must match it. Fallback at render time is English; the parity
  test makes fallback an emergency net, not a routine.
- Resolution order (see `src/brieftaube/i18n.py`): `locale` cookie →
  `Accept-Language` (region suffixes ignored) → `BRIEFTAUBE_DEFAULT_LOCALE`.
- Switching locales is a link (`/locale/{locale}`) that sets a cookie and
  redirects — a plain HTML flow, no JS required.
- Adding a locale = new catalog file + entry in `SUPPORTED_LOCALES` + all
  keys translated; the parity test then guards it like the others.
- Dates/numbers are formatted per locale in the template layer when the UI
  grows beyond English-formatted output.

## Visual language

Design tokens live in `src/brieftaube/static/css/app.css` under `:root` and
are the only sanctioned source of colors, spacing, radii, and fonts:

- **Type:** system font stack; 1rem base, 1.6 line-height; headings 1.25–2rem.
- **Color:** light theme. Muted grays for structure (`--color-bg`,
  `--color-border`), one accent (`--color-accent`) for interactive states.
  Status colors for notification priorities are **pending until the domain
  model lands** and will be added as tokens (`--color-prio-*`).
- **Spacing:** `--space-1..5` (0.25–2.5rem), multiples only.
- **Components:** cards (`.hero`-style: white surface, border, small radius,
  subtle shadow), a slim sticky-capable header with brand + locale switch.

Until a component exists twice, do not abstract it — duplication is cheaper
than the wrong abstraction.

## CSS conventions

- One stylesheet (`app.css`) until size forces a split; then per-page files
  loaded by the pages that need them.
- Tokens → semantic classes; **no utility framework** and no inline styles in
  templates. BEM-ish naming (`.locale-switch a.active`) is fine, keep it flat.
- Breakpoints: only when a layout genuinely breaks — start with the content
  column capped at `60rem` and a fluid header; add media queries on demand.
- Responsive baseline: usable at 360px width, comfortable at 1440px.

## htmx rules of thumb

- `hx-get/hx-post/hx-target/hx-swap` on real links/buttons; server responds
  with HTML fragments (Jinja partials) or a redirect — the API stays JSON.
- Forms must submit without JS (progressive enhancement) — htmx only
  replaces the round-trip, it never hides required fields or state.
- Failure states return meaningful HTML or standard error codes the page can
  render inline; no `alert()`-style UX.
- `<script>` tags are a last resort and need a note in the PR describing why
  htmx could not do it.

## Testing the UI

Templates are covered by integration tests (rendered markup, locale
variants) and e2e tests for real user flows — see `docs/TESTING.md`.
