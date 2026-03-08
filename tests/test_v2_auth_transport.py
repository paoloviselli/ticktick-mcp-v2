from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ticktick_sdk.api.base import BaseTickTickClient
from ticktick_sdk.api.v2.auth import SessionToken
from ticktick_sdk.api.v2.client import TickTickV2Client
from ticktick_sdk.exceptions import TickTickAuthenticationError


@pytest.mark.unit
class TestV2AuthTransport:
    async def test_initialize_session_prefers_bootstrap_token_for_stdio(self):
        client = TickTickV2Client(
            session_token="session-token",
            username="user@example.com",
            password="secret",
            prefer_password_login=False,
        )

        with (
            patch.object(client, "verify_authentication", AsyncMock(return_value=True)),
            patch.object(client, "_refresh_session_metadata", AsyncMock()),
            patch.object(client, "authenticate", AsyncMock()) as authenticate,
        ):
            session = await client.initialize_session()

        assert session.token == "session-token"
        assert client.session is not None
        assert client.session.token == "session-token"
        authenticate.assert_not_called()

    async def test_initialize_session_prefers_password_for_http(self):
        client = TickTickV2Client(
            session_token="session-token",
            username="user@example.com",
            password="secret",
            prefer_password_login=True,
        )
        session = SessionToken(
            token="fresh-token",
            user_id="1",
            username="user@example.com",
            inbox_id="inbox1",
            created_at=datetime.now(timezone.utc),
            cookies={"t": "fresh-token"},
        )

        with (
            patch.object(client, "authenticate", AsyncMock(return_value=session)) as authenticate,
            patch.object(client, "_refresh_session_metadata", AsyncMock()),
        ):
            result = await client.initialize_session()

        assert result.token == "fresh-token"
        authenticate.assert_awaited_once_with("user@example.com", "secret")

    async def test_request_reauthenticates_once_on_auth_failure(self):
        client = TickTickV2Client(username="user@example.com", password="secret")
        response = httpx.Response(
            200,
            json={"ok": True},
            request=httpx.Request("GET", "https://api.ticktick.com/test"),
        )

        with (
            patch.object(
                BaseTickTickClient,
                "_request",
                AsyncMock(
                    side_effect=[
                        TickTickAuthenticationError("expired"),
                        response,
                    ]
                ),
            ) as base_request,
            patch.object(client, "_reauthenticate", AsyncMock()) as reauthenticate,
        ):
            result = await client._request("GET", "/test")

        assert result.status_code == 200
        assert base_request.await_count == 2
        reauthenticate.assert_awaited_once()
