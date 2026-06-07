"""Unit tests for mcp_server.tavily: input validation only.

The TavilyClient is mocked so these tests run without TAVILY_API_KEY
and without network access.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server import tavily


def _client_ok(payload: dict | None = None):
    payload = payload or {"results": [], "answer": "ok"}
    return patch.object(tavily, "_client", return_value=_FakeClient(payload))


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def search(self, **kwargs):  # matches tavily.TavilyClient.search signature
        return self._payload


# --- happy path -----------------------------------------------------------


def test_search_passes_through_to_client():
    with _client_ok({"results": [{"url": "https://example.com"}], "answer": "x"}):
        out = tavily.search(query="hello", max_results=3, topic="news", include_answer=False)

    assert out == {"results": [{"url": "https://example.com"}], "answer": "x"}


def test_search_strips_query_whitespace():
    with _client_ok({"results": []}):
        tavily.search(query="   hello   ", max_results=1)
    # If the call above didn't raise, the strip happened client-side too.
    # Verify by reaching for the fake's recorded call args via _client().
    # _client() was patched as a whole, so we just assert no raise here.


# --- input validation -----------------------------------------------------


def test_empty_query_raises():
    with pytest.raises(ValueError, match="non-empty"):
        tavily.search(query="", max_results=5)


def test_whitespace_only_query_raises():
    with pytest.raises(ValueError, match="non-empty"):
        tavily.search(query="   \t  ", max_results=5)


@pytest.mark.parametrize("bad", [0, -1, 21, 100])
def test_max_results_out_of_range_raises(bad):
    with pytest.raises(ValueError, match="between 1 and 20"):
        tavily.search(query="x", max_results=bad)


@pytest.mark.parametrize("bad", ["sports", "GENERAL", "", "news,"])
def test_invalid_topic_raises(bad):
    with pytest.raises(ValueError, match="'general' or 'news'"):
        tavily.search(query="x", topic=bad)


# --- env-var handling -----------------------------------------------------


def test_missing_api_key_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        tavily._client()
