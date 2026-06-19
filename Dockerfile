FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Resolve dependencies first for better layer caching.
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --group deploy

# Now install the project itself.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group deploy

# Runtime stage: slim base, no uv.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY prefect_flows ./prefect_flows
COPY prefect.yaml ./

EXPOSE 8080

CMD ["python", "-m", "horizon_my_mcp.server"]
