from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import importlib
import os
from unittest.mock import patch

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

import ticktick_sdk.http as http_module
import ticktick_sdk.server as server_module
from ticktick_sdk.models import Task


class FakeTickTickClient:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.connect_calls = 0
        self.disconnect_calls = 0
        self._tasks = [
            Task(
                id="a" * 24,
                projectId="inbox123",
                title="Inbox task",
                dueDate=now + timedelta(days=1),
                tags=["work"],
            ),
            Task(
                id="b" * 24,
                projectId="proj1234567890abcdef1234",
                title="Project task",
                dueDate=now + timedelta(days=2),
                tags=["personal"],
            ),
        ]

    @classmethod
    def from_settings(cls):
        return cls()

    @property
    def inbox_id(self) -> str:
        return "inbox123"

    async def connect(self) -> None:
        self.connect_calls += 1

    async def disconnect(self) -> None:
        self.disconnect_calls += 1

    async def get_inbox_tasks(self, limit: int = 100):
        return [task for task in self._tasks if task.project_id == self.inbox_id][:limit]

    async def get_all_tasks(self):
        return list(self._tasks)

    async def get_completed_tasks_in_range(self, from_date, to_date, limit: int = 100):
        return []


def make_httpx_factory(app):
    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8000",
            headers=headers,
            timeout=timeout,
            auth=auth,
        )

    return factory


@asynccontextmanager
async def running_app(app):
    async with app.router.lifespan_context(app):
        yield app


async def call_http_tool(app, name: str, arguments: dict):
    factory = make_httpx_factory(app)
    async with streamable_http_client(
        "http://127.0.0.1:8000/mcp",
        http_client=factory(),
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(name, {"params": arguments})


def build_fresh_app():
    importlib.reload(server_module)
    refreshed_http = importlib.reload(http_module)
    return refreshed_http.create_app()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streamable_http_lists_45_tools_and_calls_new_tools():
    fake_client = FakeTickTickClient()

    with patch("ticktick_sdk.client.TickTickClient.from_settings", return_value=fake_client):
        app = build_fresh_app()
        async with running_app(app):
            factory = make_httpx_factory(app)
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp",
                http_client=factory(),
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert len(tools.tools) == 45

                    inbox_result = await session.call_tool(
                        "ticktick_get_inbox_tasks",
                        {"params": {"limit": 10, "response_format": "markdown"}},
                    )
                    calendar_result = await session.call_tool(
                        "ticktick_get_calendar",
                        {"params": {"days": 7, "response_format": "markdown"}},
                    )

    assert fake_client.connect_calls >= 1
    assert fake_client.disconnect_calls >= 1
    assert "Inbox Tasks" in inbox_result.content[0].text
    assert "Calendar" in calendar_result.content[0].text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streamable_http_cold_start_simulation_reconnects_per_app():
    created_clients: list[FakeTickTickClient] = []

    def make_client():
        client = FakeTickTickClient()
        created_clients.append(client)
        return client

    with patch("ticktick_sdk.client.TickTickClient.from_settings", side_effect=make_client):
        first_app = build_fresh_app()
        second_app = build_fresh_app()

        async with running_app(first_app):
            await call_http_tool(
                first_app,
                "ticktick_get_inbox_tasks",
                {"limit": 5, "response_format": "json"},
            )
        async with running_app(second_app):
            await call_http_tool(
                second_app,
                "ticktick_get_inbox_tasks",
                {"limit": 5, "response_format": "json"},
            )

    assert len(created_clients) >= 2
    assert all(client.connect_calls == client.disconnect_calls == 1 for client in created_clients)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streamable_http_requires_bearer_token_when_configured():
    fake_client = FakeTickTickClient()

    with (
        patch.dict(os.environ, {"MCP_BEARER_TOKEN": "top-secret"}, clear=False),
        patch("ticktick_sdk.client.TickTickClient.from_settings", return_value=fake_client),
    ):
        app = build_fresh_app()
        async with running_app(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://127.0.0.1:8000",
            ) as client:
                response = await client.post(
                    "/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "pytest", "version": "1.0"},
                        },
                    },
                    headers={"Accept": "application/json, text/event-stream"},
                )

    assert response.status_code == 401
    assert response.json()["error"] == "Unauthorized"
    assert response.headers["WWW-Authenticate"] == 'Bearer realm="ticktick-mcp"'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_streamable_http_accepts_valid_bearer_token():
    fake_client = FakeTickTickClient()

    with (
        patch.dict(os.environ, {"MCP_BEARER_TOKEN": "top-secret"}, clear=False),
        patch("ticktick_sdk.client.TickTickClient.from_settings", return_value=fake_client),
    ):
        app = build_fresh_app()
        async with running_app(app):
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp",
                http_client=httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://127.0.0.1:8000",
                    headers={"Authorization": "Bearer top-secret"},
                ),
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()

    assert len(tools.tools) == 45
