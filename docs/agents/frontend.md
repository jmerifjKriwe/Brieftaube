# Frontend conventions

Load this file when touching templates, htmx, CSS, or UI text.
The "why" lives in `docs/DESIGN.md`; this file is the "how".

## Templates

- Jinja2, `src/brieftaube/templates/`. `base.html` owns `<html>`, header,
  locale switch, and the `{% block content %}`; pages extend it.
- Render through the `render()` helper in `main.py` — it injects `t`,
  `locale`, and `supported_locales`. Do not construct `TemplateResponse`
  directly in features.
- Partials for htmx fragments: `_fragment-name.html` (leading underscore),
  rendered by dedicated handlers that return only the fragment.
- Keep logicless: no loops over complex structures, no formatting logic —
  Python prepares data, templates display it.

## Adding UI text (the i18n workflow)

1. Add the key to **`en.json` and `de.json`** in `src/brieftaube/locales/`.
2. Use it in the template: `{{ t("index.welcome") }}`, with placeholders as
   `{{ t("index.greeting", name=user.name) }}`.
3. If the page shows data differently per locale (dates, numbers), format in
   the view layer per `locale`, not in the template.
4. `just test` — the parity test rejects missing keys in either catalog.

Never: hardcoded strings in templates, English fallback text in Python,
concatenated sentence fragments (translators can't reorder them).

## htmx

- Attributes on real `<button>`/`<a>` elements; every htmx flow must degrade
  to a plain request without JS.
- Server responds with a fragment (Jinja partial), a 303 redirect, or a
  small inline error fragment — never raw JSON to the UI.
- Use `hx-boost`/OOB swaps sparingly; if a flow needs more than two
  attributes to work, prefer a full page render (this app is cheap to
  re-render).
- No `<script>` without a PR-note justification (see `docs/DESIGN.md`).

## CSS

- Tokens only (`src/brieftaube/static/css/app.css`, `:root`); no hardcoded
  colors/spacing in rules, no inline styles in templates.
- Add a semantic class to the component you're styling; don't stack
  selectors three deep.
- Dark mode, status colors for priorities: pending until the domain lands —
  add as tokens then.

## Testing your change

- Integration test asserts rendered markup incl. a non-English variant
  (see `tests/integration/test_app.py` for the pattern).
- Flows that a user performs in the browser get an e2e test
  (`tests/e2e/`), sparingly — see `docs/TESTING.md`.
