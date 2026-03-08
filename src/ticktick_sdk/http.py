"""
ASGI entrypoint for serving the TickTick MCP over Streamable HTTP.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from ticktick_sdk.server import get_streamable_http_app


def create_app() -> Starlette:
    """Create the Streamable HTTP ASGI app with browser-compatible CORS."""
    app = get_streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )
    return app


app = create_app()

