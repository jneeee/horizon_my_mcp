# horizon_my_mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes
[Tavily](https://tavily.com) and [Firecrawl](https://www.firecrawl.dev) web search
and extraction, deployable to both [Prefect Horizon](https://horizon.prefect.io)
and [FastMCP Cloud](https://fastmcp.cloud).

The project uses the [`uv`](https://docs.astral.sh/uv/) toolchain end-to-end
(`uv_build` backend, `src/` layout, `[dependency-groups]` for dev/deploy),
following the conventions in `coding-flow` skill's `references/user-defaults.md`.

## What is in the repo

| Path | Purpose |
| --- | --- |
| `src/horizon_my_mcp/server.py` | FastMCP 3.x server (`web_search`, `web_extract`, `web_agent`, `tavily_search`). Single source of truth for tool registration. |
| `src/horizon_my_mcp/firecrawl_client.py` | Thin wrapper around `firecrawl-py` (search / scrape / agent), keyless-aware. |
| `src/horizon_my_mcp/tavily_client.py` | Thin wrapper around the official `tavily-python` SDK. |
| `src/horizon_my_mcp/cli.py` | `python -m horizon_my_mcp` entry point. |
| `fastmcp.json` | FastMCP Cloud project config (points at `src/server.py` + `create_server` factory). |
| `prefect_flows/flows.py` | Prefect flow that smoke-tests the MCP server. |
| `prefect.yaml` | Declarative Prefect deployment consumed by `prefect deploy`. |
| `Dockerfile` | Multi-stage container image (uv builder → slim runtime). |
| `.dockerignore` | Excludes `.venv`, `.git`, caches, secrets. |
| `pyproject.toml` | `uv_build` backend; deps in `[project.dependencies]`; groups in `[dependency-groups]`. |
| `.github/workflows/deploy.yml` | Continuous deployment to Prefect Horizon. |

## Local quickstart (uv)

```bash
# 1. Sync deps + install the project editable
uv sync --group dev          # add --group deploy for Prefect

# 2. Run the MCP server over stdio
uv run python -m horizon_my_mcp.server

# 3. Or run via the console script
uv run horizon-mcp
```

The server speaks MCP over stdio. Point any MCP-capable client
(Claude Desktop, Cursor, MCP Inspector, …) at `uv run python -m horizon_my_mcp.server`.

> **Note on filenames:** `src/horizon_my_mcp/firecrawl_client.py` and
> `tavily_client.py` are deliberately suffixed with `_client`. Naming them
> `firecrawl.py` / `tavily.py` would shadow the top-level `firecrawl` and
> `tavily` SDK packages when Python resolves `from firecrawl import …`
> relative to our own package.

## FastMCP Cloud deployment

`fastmcp.json` is the canonical project config and tells FastMCP Cloud where
the entry point lives and how to set up its environment:

```json
{
  "source":   { "path": "src/server.py", "entrypoint": "create_server" },
  "environment": { "type": "uv", "project": "." },
  "deployment": { "transport": "stdio" }
}
```

To deploy on FastMCP Cloud, push the repo and connect it via the dashboard;
the published endpoint will be reachable at
`https://testmymcp.fastmcp.app/mcp`.

### Three entrypoint conventions on `src/horizon_my_mcp/server.py`

- An inferred `mcp` instance (`FastMCP("horizon-my-mcp")`) at module scope.
- A `create_server()` factory function returning a `FastMCP`.
- A `main()` / `__main__` guard for local stdio testing.

### Firecrawl keyless support

Firecrawl recently added keyless support — 1000 free credits per IP per
month, no API key required. The Firecrawl-backed tools (`web_search`,
`web_extract`, `web_agent`) automatically fall back to the keyless free
tier when `FIRECRAWL_API_KEY` is not set. To authenticate against a paid
tier instead, set `FIRECRAWL_API_KEY` in the deployment environment.

### Tool signatures

```text
web_search(
    query: str,
    limit: int = 5,                          # 1..50
    sources: list[str] | None = None,        # e.g. ["web", "news"]
    tbs: str | None = None,                  # e.g. "qdr:d" (past day)
) -> str                                      # JSON-encoded Firecrawl results

web_extract(
    urls: list[str],
    formats: list[str] | None = None,        # e.g. ["markdown", "html"]
) -> str                                      # JSON-encoded Firecrawl documents

web_agent(
    prompt: str,
    urls: list[str] | None = None,
) -> str                                      # JSON-encoded agent response

tavily_search(
    query: str,
    max_results: int = 5,                    # 1..20
    topic: str = "general",                  # "general" or "news"
    include_answer: bool = True,
) -> str                                      # JSON-encoded Tavily response
```

## Continuous deployment to Prefect Horizon

The workflow in `.github/workflows/deploy.yml` runs on every push to `main`
(and on manual dispatch). It calls `prefect deploy --all`, which reads
`prefect.yaml` and pushes the bundled flow to the work pool named
`$HORIZON_WORK_POOL` on the Prefect Horizon workspace `$PREFECT_API_URL`.

The Prefect smoke-test flow (`prefect_flows/flows.py:smoke_test`) spawns
the MCP server as a subprocess from `src/horizon_my_mcp/server.py` and
asserts all four expected tools (`web_search`, `web_extract`,
`web_agent`, `tavily_search`) appear in the `tools/list` response.

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
flow source. `FIRECRAWL_API_KEY` is optional — leave it unset to use the
Firecrawl keyless free tier.
