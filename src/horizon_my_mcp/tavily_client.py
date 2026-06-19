from __future__ import annotations

import os
from typing import Any

from tavily import TavilyClient


def _client() -> TavilyClient:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY environment variable is not set")
    return TavilyClient(api_key=api_key)


def search(
    query: str,
    max_results: int = 5,
    topic: str = "general",
    include_answer: bool = True,
) -> dict[str, Any]:
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")
    if max_results < 1 or max_results > 20:
        raise ValueError("max_results must be between 1 and 20")
    if topic not in {"general", "news"}:
        raise ValueError("topic must be 'general' or 'news'")

    return _client().search(
        query=query.strip(),
        max_results=max_results,
        topic=topic,
        include_answer=include_answer,
    )
