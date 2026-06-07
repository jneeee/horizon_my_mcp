from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import tavily

mcp = FastMCP("horizon-tavily-mcp")


@mcp.tool()
def tavily_search(
    query: str,
    max_results: int = 5,
    topic: str = "general",
    include_answer: bool = True,
) -> str:
    """Search the web with Tavily and return JSON-formatted results.

    Args:
        query: The search query.
        max_results: Number of results to return (1-20, default 5).
        topic: Either "general" or "news" (default "general").
        include_answer: Whether to include Tavily's synthesized answer.
    """
    result = tavily.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_answer=include_answer,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
