"""Browser smoke tests: the UI renders and locale switching works end to end."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def test_home_page_renders(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(page.get_by_role("heading", level=1)).to_contain_text("Welcome to Brieftaube")


def test_switching_locale_to_german(page: Page, base_url: str) -> None:
    page.goto(base_url)
    page.get_by_role("link", name="DE").click()

    expect(page.locator("html")).to_have_attribute("lang", "de")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Willkommen bei Brieftaube")
