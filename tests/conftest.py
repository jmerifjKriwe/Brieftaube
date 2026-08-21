"""Shared fixtures: application and sync HTTP test client."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brieftaube.main import create_app


@pytest.fixture
def test_app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as test_client:
        yield test_client
