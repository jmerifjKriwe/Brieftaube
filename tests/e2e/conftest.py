"""Session-scoped live server for Playwright e2e tests."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn

from brieftaube.main import create_app


@pytest.fixture(scope="session")
def base_url() -> Iterator[str]:
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    timeout = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > timeout:
            msg = "live server did not start in time"
            raise RuntimeError(msg)
        time.sleep(0.05)

    assert server.servers, "no listening socket"
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)
