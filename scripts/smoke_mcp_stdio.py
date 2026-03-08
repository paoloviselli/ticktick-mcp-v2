#!/usr/bin/env python3
"""
Simple STDIO smoke test for the TickTick MCP server.
"""

from __future__ import annotations

import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> int:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ticktick_sdk.cli", "server"],
        env=os.environ.copy(),
        cwd=os.getcwd(),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Tool count: {len(tools.tools)}")
            print("First five tools:")
            for tool in tools.tools[:5]:
                print(f"- {tool.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
