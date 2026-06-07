"""Unit tests for mcp_server.server: tavily_search tool forwarding.

The tavily.search wrapper is mocked so this test does not need a real
Tavily API key. We call the underlying function via FastMCP's tool
registry to exercise the public contract end-to-end (validation +
JSON encoding + parameter pass-through).
"""
from __future__ import annotations

import json
from unittest.mock import patch

from mcp_server.server import tavily_search


def test_tool_returns_json_string():
    payload = {"results": [{"title": "hi", "url": "https://x"}], "answer": "yo"}
    with patch("mcp_server.server.tavily.search", return_value=payload) as m:
        out = tavily_search(
            query="hello",
            max_results=2,
            topic="general",
            include_answer=True,
        )

    assert isinstance(out, str)
    assert json.loads(out) == payload

    m.assert_called_once_with(
        query="hello",
        max_results=2,
        topic="general",
        include_answer=True,
    )


def test_tool_propagates_validation_errors():
    with patch("mcp_server.server.tavily.search", side_effect=ValueError("bad")):
        import pytest

        with pytest.raises(ValueError, match="bad"):
            tavily_search(query="", max_results=5)
