"""
server.py — MCP stdio server for the Financial Agent.

Exposes DB query capabilities as MCP tools over stdin/stdout JSON-RPC.
This is the ONLY point of access to the database — all agent tool calls
go through this protocol boundary.

Start manually (for testing):
    python -m mcp_server.server

The agent spawns this as a subprocess via mcp_client.py.
"""

import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from mcp_server.db_queries import (
    get_sector_summary,
    list_companies,
    get_company_financials,
    search_companies,
    get_news_signals,
)

# ─────────────────────────────────────────────────────────────
# Server setup
# ─────────────────────────────────────────────────────────────

app = Server("financial-agent-db")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_sector_summary",
            description=(
                "Returns high-level metadata and aggregate statistics for a sector. "
                "Use this to get context on the sector as a whole before diving into companies."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                        "description": "The sector to summarize.",
                    }
                },
                "required": ["sector"],
            },
        ),
        types.Tool(
            name="list_companies",
            description=(
                "Returns all companies in a sector with their latest financial metrics. "
                "Use this to get an overview of all available companies before drilling down."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                        "description": "The sector to list companies for.",
                    }
                },
                "required": ["sector"],
            },
        ),
        types.Tool(
            name="get_company_financials",
            description=(
                "Returns full financial history and recent news signals for a specific company. "
                "If the company is not in the database, returns a clear 'not found' message — "
                "the agent MUST use this signal to honestly say it has no data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name or ticker symbol to look up.",
                    },
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                        "description": "Sector to search within.",
                    },
                },
                "required": ["company_name", "sector"],
            },
        ),
        types.Tool(
            name="search_companies",
            description=(
                "Fuzzy-searches companies by name or ticker within a sector. "
                "Use when you need to find the exact company name before calling get_company_financials."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Partial name or ticker to search for.",
                    },
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                        "description": "Sector to search within.",
                    },
                },
                "required": ["query", "sector"],
            },
        ),
        types.Tool(
            name="get_news_signals",
            description=(
                "Returns recent news and signals (hiring, layoffs, earnings beats/misses, "
                "expansions, acquisitions) for a specific company. "
                "Use for headcount questions, recent developments, or momentum analysis."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Company name or ticker to retrieve signals for.",
                    },
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                        "description": "Sector (optional but improves lookup accuracy).",
                    },
                },
                "required": ["company_name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    try:
        if name == "get_sector_summary":
            result = get_sector_summary(arguments["sector"])

        elif name == "list_companies":
            result = list_companies(arguments["sector"])

        elif name == "get_company_financials":
            result = get_company_financials(
                arguments["company_name"], arguments["sector"]
            )

        elif name == "search_companies":
            result = search_companies(arguments["query"], arguments["sector"])

        elif name == "get_news_signals":
            result = get_news_signals(
                arguments["company_name"],
                arguments.get("sector"),
            )

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        result = {"error": str(e), "tool": name, "arguments": arguments}

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
