"""Lightweight i18n for the server-rendered UI.

Catalogs are plain JSON files in ``src/brieftaube/locales``. English (``en``)
is the source language: every UI key must exist there. Missing keys in other
locales fall back to English at render time; ``tests/unit/test_i18n.py``
enforces key parity between catalogs so fallbacks stay an emergency net.

Usage in templates::

    {{ t("index.welcome") }}
    {{ t("index.greeting", name=user.name) }}
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

DEFAULT_LOCALE = "en"
FALLBACK_LOCALE = "en"

# Adding a locale = add a JSON catalog here + extend this tuple.
# See docs/DESIGN.md ("Internationalization").
SUPPORTED_LOCALES = ("en", "de")

LOCALES_DIR = Path(__file__).parent / "locales"


@cache
def load_catalog(locale: str) -> dict[str, str]:
    """Load a translation catalog; missing locale falls back to English."""
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        path = LOCALES_DIR / f"{FALLBACK_LOCALE}.json"
    catalog: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    return catalog


def translate(locale: str, key: str, /, **placeholders: str) -> str:
    """Translate ``key`` for ``locale``, formatting named placeholders.

    Falls back to English (then to the key itself) when a translation is
    missing. Raises ``KeyError`` for missing placeholders — a bug we want
    to surface in tests, never silently.
    """
    catalog = load_catalog(locale)
    template = catalog.get(key) or load_catalog(FALLBACK_LOCALE).get(key) or key
    return template.format_map(placeholders)


def normalize_locale(
    cookie_locale: str | None = None,
    accept_language: str | None = None,
    default: str = DEFAULT_LOCALE,
) -> str:
    """Pick the UI locale: explicit cookie wins, then Accept-Language, then default.

    Accept-Language is parsed as ``language[-region]`` pairs with optional
    quality values, e.g. ``de-DE,de;q=0.9,en;q=0.8``. Region suffixes are
    ignored (``de-AT`` matches ``de``).
    """
    supported = set(SUPPORTED_LOCALES)
    if cookie_locale and cookie_locale in supported:
        return cookie_locale

    if accept_language:
        parsed: list[tuple[float, str]] = []
        for part in accept_language.split(","):
            tokens = [t.strip() for t in part.split(";")]
            lang = tokens[0].lower()
            q = 1.0
            for param in tokens[1:]:
                if param.startswith("q="):
                    try:
                        q = float(param[2:])
                    except ValueError:
                        q = 0.0
            parsed.append((q, lang))
        for q, lang in sorted(parsed, key=lambda item: item[0], reverse=True):
            if q <= 0:
                continue
            base = lang.split("-", 1)[0]
            if base in supported:
                return base

    return default
