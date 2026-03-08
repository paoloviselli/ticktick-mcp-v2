"""
ASGI entrypoint for serving the TickTick MCP over Streamable HTTP.
"""

from __future__ import annotations

import os
import secrets

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from ticktick_sdk.server import get_streamable_http_app


class UrlKeyAuthMiddleware:
    """Protect the HTTP MCP endpoint with a static URL key when configured."""

    def __init__(self, app: ASGIApp, url_key: str) -> None:
        self.app = app
        self.url_key = url_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        provided_key = request.query_params.get("key", "")
        if not secrets.compare_digest(provided_key, self.url_key):
            response = JSONResponse(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid MCP URL key.",
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def create_app() -> Starlette:
    """Create the Streamable HTTP ASGI app with browser-compatible CORS."""
    app = get_streamable_http_app()
    url_key = os.environ.get("MCP_URL_KEY", "").strip()
    if url_key:
        app.add_middleware(UrlKeyAuthMiddleware, url_key=url_key)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    return app


app = create_app()
