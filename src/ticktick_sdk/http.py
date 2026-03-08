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


class BearerTokenAuthMiddleware:
    """Protect the HTTP MCP endpoint with a static bearer token when configured."""

    def __init__(self, app: ASGIApp, bearer_token: str) -> None:
        self.app = app
        self.bearer_token = bearer_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {self.bearer_token}"
        if not secrets.compare_digest(auth_header, expected):
            response = JSONResponse(
                {
                    "error": "Unauthorized",
                    "message": "Missing or invalid bearer token.",
                },
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="ticktick-mcp"'},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def create_app() -> Starlette:
    """Create the Streamable HTTP ASGI app with browser-compatible CORS."""
    app = get_streamable_http_app()
    bearer_token = os.environ.get("MCP_BEARER_TOKEN", "").strip()
    if bearer_token:
        app.add_middleware(BearerTokenAuthMiddleware, bearer_token=bearer_token)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    return app


app = create_app()
