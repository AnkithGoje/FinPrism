"""
mcp_client.py — Subprocess-based MCP client for the Financial Agent.

Spawns mcp_server/server.py as a child process and communicates via
stdin/stdout using MCP's JSON-RPC protocol.

This is the ONLY way the agent should access the database.
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Path to the MCP server module
PROJECT_ROOT = Path(__file__).parent.parent
SERVER_MODULE = "mcp_server.server"


@asynccontextmanager
async def get_mcp_session():
    """Context manager that yields a live MCP ClientSession."""
    server_params = StdioServerParameters(
        command=sys.executable,          # same python interpreter
        args=["-m", SERVER_MODULE],
        env=None,
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Call a single MCP tool and return parsed result."""
    async with get_mcp_session() as session:
        result = await session.call_tool(tool_name, arguments)

    # MCP returns a list of content items; we expect text JSON
    if result.content and hasattr(result.content[0], "text"):
        return json.loads(result.content[0].text)
    return {"error": "Empty or unexpected MCP response"}


async def call_tools_batch(
    calls: list[tuple[str, dict[str, Any]]]
) -> list[Any]:
    """
    Call multiple MCP tools in a SINGLE session (efficient).
    calls: list of (tool_name, arguments) tuples
    """
    results = []
    async with get_mcp_session() as session:
        for tool_name, arguments in calls:
            result = await session.call_tool(tool_name, arguments)
            if result.content and hasattr(result.content[0], "text"):
                results.append(json.loads(result.content[0].text))
            else:
                results.append({"error": "Empty MCP response"})
    return results


# ─────────────────────────────────────────────────────────────
# Convenience sync wrappers (safe across sync & async callers)
# ─────────────────────────────────────────────────────────────

def _run_coro_sync(coro):
    # ponytail: if an event loop is running (FastAPI/Jupyter), run in worker thread to avoid loop collision
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


def call_tool_sync(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Synchronous wrapper around call_tool."""
    return _run_coro_sync(call_tool(tool_name, arguments))


def call_tools_batch_sync(calls: list[tuple[str, dict[str, Any]]]) -> list[Any]:
    """Synchronous wrapper around call_tools_batch."""
    return _run_coro_sync(call_tools_batch(calls))


# ─────────────────────────────────────────────────────────────
# Quick smoke test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing MCP client — calling get_sector_summary for 'tech'...")
    result = call_tool_sync("get_sector_summary", {"sector": "tech"})
    print(json.dumps(result, indent=2))
