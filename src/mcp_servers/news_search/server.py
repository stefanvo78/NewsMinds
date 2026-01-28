"""
MCP Server for News Search.

This server exposes news search capabilities as MCP tools that
Claude (or any MCP-compatible LLM) can use.
"""

import json
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
)
import httpx

# Create the MCP server
server = Server("news-search")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available tools.

    MCP clients call this to discover what tools this server provides.
    """
    return [
        Tool(
            name="search_news",
            description="Search for news articles on a given topic. Returns headlines and summaries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'artificial intelligence', 'climate change')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_trending_topics",
            description="Get currently trending news topics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "News category (technology, business, science, health)",
                        "enum": ["technology", "business", "science", "health"],
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls from the LLM.

    When Claude decides to use a tool, this function executes it.
    """
    if name == "search_news":
        return await handle_search_news(arguments)
    elif name == "get_trending_topics":
        return await handle_trending_topics(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_search_news(arguments: dict) -> list[TextContent]:
    """Execute a news search."""
    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 5)

    # In production, you'd call a real news API here
    # For now, we'll simulate with a placeholder
    # Replace this with your actual news API integration

    # Example using NewsAPI.org (you'd need an API key):
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(
    #         "https://newsapi.org/v2/everything",
    #         params={"q": query, "pageSize": max_results},
    #         headers={"X-Api-Key": NEWS_API_KEY},
    #     )
    #     data = response.json()

    # Simulated response for demo
    results = {
        "query": query,
        "articles": [
            {
                "title": f"News about {query} - Article 1",
                "summary": f"This is a summary about {query}...",
                "source": "Example News",
                "url": "https://example.com/article1",
            },
            {
                "title": f"Breaking: {query} developments",
                "summary": f"Latest updates on {query}...",
                "source": "Tech Daily",
                "url": "https://example.com/article2",
            },
        ][:max_results],
    }

    return [
        TextContent(
            type="text",
            text=json.dumps(results, indent=2),
        )
    ]


async def handle_trending_topics(arguments: dict) -> list[TextContent]:
    """Get trending topics."""
    category = arguments.get("category", "technology")

    # Simulated trending topics
    topics = {
        "technology": ["AI Safety", "Quantum Computing", "Electric Vehicles"],
        "business": ["Interest Rates", "Tech Layoffs", "Crypto Markets"],
        "science": ["Mars Mission", "Climate Research", "Gene Therapy"],
        "health": ["New Vaccines", "Mental Health", "Drug Pricing"],
    }

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "category": category,
                    "trending": topics.get(category, []),
                },
                indent=2,
            ),
        )
    ]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
