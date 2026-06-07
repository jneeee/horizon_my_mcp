FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY mcp_server ./mcp_server
COPY prefect_flows ./prefect_flows
COPY prefect.yaml ./

RUN pip install --upgrade pip && pip install -e ".[deploy]"

EXPOSE 8080

CMD ["python", "-m", "mcp_server.server"]
