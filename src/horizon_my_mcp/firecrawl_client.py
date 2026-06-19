from __future__ import annotations

import json
import os
from typing import Any

from firecrawl import Firecrawl
from firecrawl.v2.client import FirecrawlClient

# The top-level ``Firecrawl`` class eagerly constructs a V1 client that rejects
# ``api_key=None`` (ValueError("No API key provided")). The V2 client supports
# keyless mode — when ``api_key`` is None and no env var is set, ``scrape``,
# ``search``, and ``agent`` fall back to the keyless free tier (rate-limited
# per IP). To support keyless, we use ``FirecrawlClient`` directly when no key
# is present, and the full ``Firecrawl`` class only when an explicit key is
# available.

_DEFAULT_LIMIT = 5
_MAX_LIMIT = 50


def _client() -> FirecrawlClient:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if api_key:
        return Firecrawl(api_key=api_key)
    return FirecrawlClient(api_key=None)


def search(
    query: str,
    limit: int = _DEFAULT_LIMIT,
    sources: list[str] | None = None,
    tbs: str | None = None,
) -> dict[str, Any]:
    """Search the web via Firecrawl and return JSON-serializable results.

    Uses the v2 ``FirecrawlClient.search`` endpoint. Falls back to Firecrawl's
    keyless free tier when ``FIRECRAWL_API_KEY`` is not set.

    Args:
        query: The search query string.
        limit: Maximum number of results to return (1-50, default 5).
        sources: Optional list of source types, e.g. ["web", "news", "images"].
        tbs: Optional time-based search filter (e.g. "qdr:d" for past day).
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    if limit < 1 or limit > _MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {_MAX_LIMIT}")

    result = _client().search(
        query=query.strip(),
        limit=limit,
        sources=sources,
        tbs=tbs,
    )
    return json.loads(json.dumps(result, default=lambda o: getattr(o, "__dict__", str(o))))


def extract(
    urls: list[str],
    formats: list[str] | None = None,
) -> dict[str, Any]:
    """Scrape one or more URLs via Firecrawl and return JSON-serializable content.

    The v2 SDK ``scrape`` takes a single URL, so this wrapper iterates over the
    list and collects the documents into a single payload.

    Args:
        urls: One or more URLs to scrape.
        formats: Optional list of output formats (e.g. ["markdown", "html"]).
    """
    if not urls:
        raise ValueError("urls must be a non-empty list")
    if not all(isinstance(u, str) and u.strip() for u in urls):
        raise ValueError("each url must be a non-empty string")

    client = _client()
    documents: list[Any] = []
    for url in urls:
        doc = client.scrape(url.strip(), formats=formats)
        documents.append(doc)

    return {
        "documents": [
            json.loads(json.dumps(d, default=lambda o: getattr(o, "__dict__", str(o))))
            for d in documents
        ],
        "count": len(documents),
    }


def agent(
    prompt: str,
    urls: list[str] | None = None,
) -> dict[str, Any]:
    """Run a Firecrawl agent and return JSON-serializable results.

    Uses the v2 ``FirecrawlClient.agent`` method when available. The agent takes
    a natural-language ``prompt`` and an optional list of seed ``urls``.

    Args:
        prompt: Natural-language instruction for the agent.
        urls: Optional list of seed URLs to constrain the agent.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    result = _client().agent(urls=urls, prompt=prompt.strip())
    return json.loads(json.dumps(result, default=lambda o: getattr(o, "__dict__", str(o))))
