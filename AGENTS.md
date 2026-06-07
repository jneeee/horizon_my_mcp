# AGENTS.md — Instructions for AI coding agents

This repo packages a [Model Context Protocol](https://modelcontextprotocol.io) server
that exposes [Tavily](https://tavily.com) web search, with continuous deployment
to [Prefect Horizon](https://horizon.prefect.io).

## Repo layout

| Path | Purpose |
| --- | --- |
| `mcp_server/server.py` | FastMCP server, `tavily_search` tool, stdio transport. |
| `mcp_server/tavily.py` | Thin wrapper over the official `tavily-python` SDK. |
| `mcp_server/cli.py` | `python -m mcp_server` entry point. |
| `prefect_flows/flows.py` | Smoke-test flow (`tools/list` round-trip). |
| `prefect.yaml` | Declarative Prefect deployment (push/pull steps + cron). |
| `Dockerfile` | Multi-stage uv image, runs the MCP server. |
| `.github/workflows/ci.yml` | Lint + lock check + pytest on every push/PR. |
| `.github/workflows/deploy.yml` | `prefect deploy --all` on push to `main`. |
| `pyproject.toml` | uv build backend, runtime deps, dependency groups. |
| `uv.lock` | Pinned lockfile — committed. |
| `tests/` | pytest suite for `mcp_server.tavily` and `mcp_server.server`. |

## Local quickstart

This project uses [uv](https://docs.astral.sh/uv/) for everything — dependency
management, venvs, lockfile, and running tools. There is no `requirements.txt`,
no `pip install`, no virtualenv dance.

```bash
# One-time: install uv (https://docs.astral.sh/uv/#installation)
uv sync                  # creates .venv, installs [dev] group from uv.lock
uv run pytest            # run tests
uv run ruff check .      # lint

export TAVILY_API_KEY=***
uv run python -m mcp_server.server    # MCP over stdio
```

Point any MCP client (Claude Desktop, Cursor, MCP Inspector) at
`uv run --project . python -m mcp_server.server` (or activate `.venv` and use
`python -m mcp_server.server`). The `tavily_search` tool will be exposed.

### Tool contract — `tavily_search`

```text
tavily_search(query: str,
              max_results: int = 5,        # 1..20
              topic: str = "general",      # "general" | "news"
              include_answer: bool = True) -> str   # JSON-encoded Tavily response
```

Validation lives in `mcp_server/tavily.py:search` (raises `ValueError` on bad
input, `RuntimeError` if `TAVILY_API_KEY` is missing). Keep it that way — the
MCP layer just forwards.

## Conventions

- **Python 3.11** — pinned in `.python-version`; CI reads it via
  `astral-sh/setup-uv`'s `version-file` option.
- **uv for everything** — build backend is `uv_build`, dependency groups in
  `[dependency-groups]`, no `[project.optional-dependencies]`.
- **No lockfile churn** — `uv.lock` is committed and CI runs `uv lock --check`
  on every push. Bump it via `uv lock --upgrade` only when you mean to.
- **Ruff** with `line-length = 100`, Python 3.11 target. Lint is enforced in CI
  (format check is intentionally not — see "Don't" below).
- **Server transport is stdio only** — do not add an HTTP/SSE listener.
- **Inputs are validated at the wrapper layer** (`mcp_server/tavily.py`), not
  in the FastMCP tool body.

## Dependency groups

- `dev` (default) — `pytest`, `ruff`. Installed by `uv sync`.
- `deploy` — `prefect`. Install with `uv sync --group deploy`; needed to run
  the Prefect flow or the deploy workflow locally.

## Testing

```bash
uv run pytest                          # 15 tests, runs offline
uv run pytest --cov=mcp_server --cov-report=term-missing   # with coverage
```

`tests/conftest.py` exports a fake `TAVILY_API_KEY` so the suite has no
external dependency. Tests that assert the "missing key" path explicitly
delete the env var with `monkeypatch.delenv(...)`.

The Prefect smoke flow is **not** covered by the unit suite — it requires
Prefect runtime and is exercised by `prefect deploy --all` in CI.

## CI

`.github/workflows/ci.yml` runs on every push and PR to `main`:

1. `uv sync --frozen` (uses committed lockfile).
2. `uv lock --check` (catches unpushed lockfile changes).
3. `uv run ruff check .` (lint, fail-fast on new issues).
4. `uv run pytest` (15 tests, mock-based, offline).

`.github/workflows/deploy.yml` runs on every push to `main` (and manual
dispatch). It mirrors CI but adds the `deploy` group, runs Prefect
preflight checks, then `prefect deploy --all`.

## Deployment

The deploy workflow reads the same four repo variables/secrets as before —
**never commit them**:

| Location | Key | Purpose |
| --- | --- | --- |
| Actions → Variables | `PREFECT_API_URL` | e.g. `https://api.prefect.cloud/workspace/<id>`. |
| Actions → Variables | `HORIZON_WORK_POOL` | Target work pool on Horizon. |
| Actions → Secrets | `PREFECT_API_KEY` | Prefect Cloud API key. |
| Actions → Secrets | `TAVILY_API_KEY` | Forwarded to the flow run and to long-running MCP workers. |

`TAVILY_API_KEY` is consumed both by the smoke flow and by any long-running
MCP worker image; configure it on the work pool/worker, not in flow source.

## Common tasks

- **Add a new tool** — define it in `mcp_server/tavily.py` (or a sibling
  module), wrap it in `mcp_server/server.py` with `@mcp.tool()`, add a test
  in `tests/`, document the signature in `README.md` and here.
- **Tweak the schedule** — edit the `cron`/`timezone` block under
  `deployments` in `prefect.yaml`; do not hardcode it in the workflow.
- **Add a runtime dep** — `uv add <pkg>`; this updates `pyproject.toml` and
  `uv.lock` in one shot. Commit both.
- **Add a dev-only dep** — `uv add --group dev <pkg>`.
- **Bump everything** — `uv lock --upgrade && uv sync`.

## Don't

- Don't add HTTP/SSE transports, auth layers, or a separate web server.
  Horizon handles ingress for MCP clients.
- Don't introduce a second build backend, lockfile manager, or `pip` /
  `requirements.txt` workflow. uv is the only tool.
- Don't run `ruff format` on pre-existing files just to satisfy CI — the
  format check is intentionally off in CI; only lint is enforced. If you
  touch a file's logic, leave its style alone.
- Don't commit secrets, `.prefect/`, `.venv/`, or any local cache (already
  covered by `.gitignore`).
- Don't bump `uv.lock` without a matching `pyproject.toml` change (and vice
  versa) — CI's `uv lock --check` will fail otherwise.
