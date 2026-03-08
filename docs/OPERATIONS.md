# TickTick MCP Operations

## Local STDIO

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
ticktick-sdk
```

Use this mode for Codex Desktop and Claude Desktop.

## Local Streamable HTTP

```bash
. .venv/bin/activate
ticktick-sdk server --transport streamable-http --bind-host 0.0.0.0 --bind-port 8000
```

This serves the MCP endpoint at `http://127.0.0.1:8000/mcp`.

## Auth Notes

- `TICKTICK_ACCESS_TOKEN` is required for the V1 API.
- `TICKTICK_USERNAME` and `TICKTICK_PASSWORD` are the dependable V2 auth path.
- `TICKTICK_V2_SESSION_TOKEN` is optional and used to bootstrap warm sessions.
- HTTP/stateless deployments re-authenticate with username/password on cold starts.
- `MCP_URL_KEY` is optional but recommended for any public HTTP deployment.

## Vercel

- The ASGI entrypoint is `api/index.py`.
- Configure all TickTick env vars in the Vercel project.
- Add `PUBLIC_BASE_URL=https://YOUR-APP.vercel.app`.
- Add `MCP_URL_KEY=<long-random-secret>` to block unauthenticated access.
- The deployed MCP endpoint is `/mcp`.

## Railway

Use the shared ASGI app:

```bash
uvicorn ticktick_sdk.http:app --host 0.0.0.0 --port $PORT
```

## Smoke Checks

STDIO:

```bash
. .venv/bin/activate
python scripts/smoke_mcp_stdio.py
```

HTTP:

```bash
. .venv/bin/activate
pytest tests/test_server_http.py -q
```

## Troubleshooting

- Inbox issues: call `ticktick_get_status` first and verify `inbox_id` is present, then call `ticktick_get_inbox_tasks`.
- V2 auth failures on HTTP: confirm username/password are present and valid even if `TICKTICK_V2_SESSION_TOKEN` is set.
- Tool count drift: the current MCP surface should list 45 tools.
- `401 Unauthorized` from `/mcp`: confirm the connector URL includes `?key=<MCP_URL_KEY>`.
