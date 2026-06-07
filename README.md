# horizon_my_mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes
[Tavily](https://tavily.com) web search, packaged for continuous deployment to
[Prefect Horizon](https://horizon.prefect.io).

## What is in the repo

| Path | Purpose |
| --- | --- |
| `mcp_server/server.py` | FastMCP server with a `tavily_search` tool. |
| `mcp_server/tavily.py` | Thin wrapper around the official `tavily-python` SDK. |
| `prefect_flows/flows.py` | Prefect flow that smoke-tests the MCP server. |
| `prefect.yaml` | Declarative Prefect deployment consumed by `prefect deploy`. |
| `Dockerfile` | Container image for the MCP server / Prefect worker. |
| `.github/workflows/deploy.yml` | Continuous deployment to Prefect Horizon. |

## Local quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[deploy]"

export TAVILY_API_KEY="tvly-..."
python -m mcp_server.server
```

The server speaks MCP over stdio. Point any MCP-capable client
(Claude Desktop, Cursor, MCP Inspector, …) at `python -m mcp_server.server`
and you will see the `tavily_search` tool.

### Tool signature

```text
tavily_search(
    query: str,
    max_results: int = 5,        # 1..20
    topic: str = "general",      # "general" or "news"
    include_answer: bool = True,
) -> str                         # JSON-encoded Tavily response
```

## Continuous deployment to Prefect Horizon

The workflow in `.github/workflows/deploy.yml` runs on every push to `main`
(and on manual dispatch). It calls `prefect deploy --all`, which reads
`prefect.yaml` and pushes the bundled flow to the work pool named
`$HORIZON_WORK_POOL` on the Prefect Horizon workspace
`$PREFECT_API_URL`.

### Required repository configuration

Set these in the GitHub repository settings — **do not** commit any
secrets.

| Location | Key | Purpose |
| --- | --- | --- |
| Actions → Variables | `PREFECT_API_URL` | Workspace URL, e.g. `https://api.prefect.cloud/workspace/<id>`. |
| Actions → Variables | `HORIZON_WORK_POOL` | Target work pool name on Horizon. |
| Actions → Secrets | `PREFECT_API_KEY` | Prefect Cloud API key. |
| Actions → Secrets | `TAVILY_API_KEY` | Tavily API key forwarded to the flow run. |

`TAVILY_API_KEY` is also passed to long-running MCP workers that pull the
deployment image; configure it on the work pool or worker, not in the
flow source.
