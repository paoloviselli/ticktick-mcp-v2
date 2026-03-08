from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from ticktick_sdk import cli


@pytest.mark.unit
def test_run_server_forwards_streamable_http_options():
    original_enabled = os.environ.pop("TICKTICK_ENABLED_TOOLS", None)

    try:
        with patch("ticktick_sdk.server.main") as server_main:
            exit_code = cli.run_server(
                enabled_tools="ticktick_get_inbox_tasks",
                transport="streamable-http",
                bind_host="0.0.0.0",
                bind_port=9000,
                mount_path="/mcp",
            )
    finally:
        os.environ.pop("TICKTICK_ENABLED_TOOLS", None)
        if original_enabled is not None:
            os.environ["TICKTICK_ENABLED_TOOLS"] = original_enabled

    assert exit_code == 0
    server_main.assert_called_once_with(
        transport="streamable-http",
        bind_host="0.0.0.0",
        bind_port=9000,
        mount_path="/mcp",
    )
