"""Integration tests for the application shell: health, rendering, i18n."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_renders_english_by_default(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="en"' in response.text
    assert "Welcome to Brieftaube" in response.text


def test_index_renders_german_from_cookie(client: TestClient) -> None:
    client.cookies.set("locale", "de")
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="de"' in response.text
    assert "Willkommen bei Brieftaube" in response.text


def test_index_renders_german_from_accept_language(client: TestClient) -> None:
    response = client.get("/", headers={"Accept-Language": "de-DE,de;q=0.9,en;q=0.8"})
    assert response.status_code == 200
    assert "Willkommen bei Brieftaube" in response.text


def test_set_locale_sets_cookie_and_redirects(client: TestClient) -> None:
    response = client.get("/locale/de", follow_redirects=False)
    assert response.status_code == 303
    assert "locale=de" in response.headers["set-cookie"]

    client.cookies.set("locale", "de")
    followed = client.get("/")
    assert "Willkommen bei Brieftaube" in followed.text


def test_set_locale_rejects_unsupported_locale(client: TestClient) -> None:
    assert client.get("/locale/xx").status_code == 404
