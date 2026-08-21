"""FastAPI application factory and root routes.

The retry/escalation loop and the MQTT consumer will be started in the
lifespan handler once implemented - see docs/concepts/architecture.md sections
3 and 4.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from brieftaube.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale, translate

_BASE_DIR = Path(__file__).parent

templates = Jinja2Templates(directory=_BASE_DIR / "templates")

_LOCALE_COOKIE = "locale"
_LOCALE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # one year


class LocaleMiddleware(BaseHTTPMiddleware):
    """Resolve the request locale once and expose it as ``request.state.locale``."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.locale = normalize_locale(
            cookie_locale=request.cookies.get(_LOCALE_COOKIE),
            accept_language=request.headers.get("accept-language"),
        )
        return await call_next(request)


def render(request: Request, template_name: str, /, **context: object) -> HTMLResponse:
    """Render a template with the i18n globals (``t``, ``locale``) preloaded."""
    locale = getattr(request.state, "locale", DEFAULT_LOCALE)
    context.setdefault("t", partial(translate, locale))
    context.setdefault("locale", locale)
    context.setdefault("supported_locales", SUPPORTED_LOCALES)
    return templates.TemplateResponse(request, template_name, context=context)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup: spawn asyncio background tasks (retry loop, MQTT consumer).
    yield
    # Shutdown: cancel background tasks.


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(title="Brieftaube", version="0.1.0", lifespan=lifespan)
    app.add_middleware(LocaleMiddleware)
    app.mount("/static", StaticFiles(directory=_BASE_DIR / "static"), name="static")

    @app.get("/healthz", tags=["meta"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    async def index(request: Request) -> HTMLResponse:
        return render(request, "index.html")

    @app.get("/locale/{locale}", include_in_schema=False)
    async def set_locale(locale: str) -> RedirectResponse:
        if locale not in SUPPORTED_LOCALES:
            raise HTTPException(status_code=404)
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(_LOCALE_COOKIE, locale, max_age=_LOCALE_COOKIE_MAX_AGE)
        return response

    return app


app = create_app()
