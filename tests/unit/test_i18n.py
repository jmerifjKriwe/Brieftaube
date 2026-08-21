"""Guard rails for translation catalogs and locale resolution.

These tests keep the multilingual UI cheap to maintain: key parity between
catalogs is enforced by tests, not by reviewer discipline.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from brieftaube import i18n
from brieftaube.i18n import (
    DEFAULT_LOCALE,
    LOCALES_DIR,
    SUPPORTED_LOCALES,
    normalize_locale,
    translate,
)


def test_every_supported_locale_has_a_catalog() -> None:
    for locale in SUPPORTED_LOCALES:
        assert (LOCALES_DIR / f"{locale}.json").exists(), f"missing catalog for {locale!r}"


def test_catalogs_have_identical_keys() -> None:
    reference = i18n.load_catalog(DEFAULT_LOCALE)
    for locale in SUPPORTED_LOCALES:
        catalog = i18n.load_catalog(locale)
        assert set(catalog) == set(reference), (
            f"catalog {locale!r} diverges from {DEFAULT_LOCALE!r}: "
            f"only-in-{locale}={sorted(set(catalog) - set(reference))}, "
            f"missing-in-{locale}={sorted(set(reference) - set(catalog))}"
        )


def test_catalogs_contain_no_empty_values() -> None:
    for locale in SUPPORTED_LOCALES:
        for key, value in i18n.load_catalog(locale).items():
            assert value.strip(), f"empty translation for {key!r} in {locale!r}"


def test_translate_returns_key_for_unknown_key() -> None:
    assert translate("de", "does.not.exist") == "does.not.exist"


@pytest.fixture(autouse=True)
def _clear_catalog_cache() -> Iterator[None]:
    """Keep the lru_cache from leaking catalogs between tests."""
    yield
    i18n.load_catalog.cache_clear()


def test_translate_formats_named_placeholders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(i18n, "LOCALES_DIR", tmp_path)
    (tmp_path / "en.json").write_text(json.dumps({"greet": "Hello, {name}!"}), encoding="utf-8")
    i18n.load_catalog.cache_clear()
    assert translate("en", "greet", name="Ada") == "Hello, Ada!"


@pytest.mark.parametrize(
    ("cookie", "accept_language", "expected"),
    [
        ("de", None, "de"),  # explicit cookie wins
        ("de", "en-US,en;q=0.9", "de"),
        (None, "de-DE,de;q=0.9,en;q=0.8", "de"),  # region prefix is stripped
        (None, "fr-CH,de;q=0.5", "de"),  # unsupported lang skipped
        (None, "fr", DEFAULT_LOCALE),  # nothing supported -> default
        (None, None, DEFAULT_LOCALE),
        ("xx", None, DEFAULT_LOCALE),  # garbage cookie -> default
    ],
)
def test_normalize_locale(cookie: str | None, accept_language: str | None, expected: str) -> None:
    assert normalize_locale(cookie_locale=cookie, accept_language=accept_language) == expected
