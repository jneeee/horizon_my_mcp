"""Prefect flow that smoke-tests the MCP server.

This is the unit of work that Prefect Horizon schedules. The flow boots
the MCP server in stdio mode, sends a single `tools/list` request, and
shuts it down. A successful run proves the bundled server is importable
and that the client libraries (Tavily / Firecrawl) can be initialised
with the configured keys (or the Firecrawl keyless free tier when no
key is set).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from prefect import flow, get_run_logger

# After the src/ layout migration, the MCP server entry point is
# `python -m horizon_my_mcp.server`. We resolve the file relative to the
# project root, which is the parent of `prefect_flows/` for both the
# editable install and the Prefect image.
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_ENTRY = REPO_ROOT / "src" / "horizon_my_mcp" / "server.py"

LIST_TOOLS_REQUEST = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize",'
    '"params":{"protocolVersion":"2024-11-05",'
    '"capabilities":{},"clientInfo":{"name":"horizon-smoke","version":"0.1.0"}}}\n'
    '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
)


@flow(name="horizon-my-mcp-smoke", log_prints=True)
def smoke_test() -> dict:
    """Boot the MCP server, list its tools, and exit."""
    logger = get_run_logger()

    logger.info("Starting MCP server smoke test from %s", SERVER_ENTRY)
    proc = subprocess.run(
        [sys.executable, str(SERVER_ENTRY)],
        input=LIST_TOOLS_REQUEST,
        text=True,
        capture_output=True,
        timeout=30,
        env=os.environ,
    )

    stdout = proc.stdout
    if proc.returncode != 0 and not stdout:
        raise RuntimeError(
            f"MCP server exited with {proc.returncode}: {proc.stderr.strip()}"
        )

    tool_names: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            import json

            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        result = payload.get("result", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if tools:
            tool_names = [t.get("name") for t in tools if isinstance(t, dict)]

    expected = {"web_search", "web_extract", "web_agent", "tavily_search"}
    missing = expected - set(tool_names)
    if missing:
        raise RuntimeError(
            f"Missing tools {missing}; got: {tool_names}. stdout={stdout!r}"
        )

    logger.info("MCP server healthy. Tools: %s", tool_names)
    return {"status": "ok", "tools": tool_names}


if __name__ == "__main__":
    smoke_test()
