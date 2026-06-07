"""Prefect flow that smoke-tests the Tavily MCP server.

This is the unit of work that Prefect Horizon schedules. The flow boots
the MCP server in stdio mode, sends a single `tools/list` request, and
shuts it down. A successful run proves the bundled server is importable
and that the Tavily client can be initialised with the configured key.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from prefect import flow, get_run_logger

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_ENTRY = REPO_ROOT / "mcp_server" / "server.py"

LIST_TOOLS_REQUEST = (
    '{"jsonrpc":"2.0","id":1,"method":"initialize",'
    '"params":{"protocolVersion":"2024-11-05",'
    '"capabilities":{},"clientInfo":{"name":"horizon-smoke","version":"0.1.0"}}}\n'
    '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
)


@flow(name="horizon-tavily-mcp-smoke", log_prints=True)
def smoke_test() -> dict:
    """Boot the MCP server, list its tools, and exit."""
    logger = get_run_logger()
    if not os.environ.get("TAVILY_API_KEY"):
        raise RuntimeError("TAVILY_API_KEY must be set in the deployment environment")

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

    if "tavily_search" not in tool_names:
        raise RuntimeError(
            f"Expected 'tavily_search' tool, got: {tool_names}. stdout={stdout!r}"
        )

    logger.info("MCP server healthy. Tools: %s", tool_names)
    return {"status": "ok", "tools": tool_names}


if __name__ == "__main__":
    smoke_test()
