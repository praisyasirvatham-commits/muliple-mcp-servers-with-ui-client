#!/usr/bin/env python3
"""
Simple MCP client for the E-Commerce MCP Server.

Lists registered MCP tools and calls the first products/list tool it finds (no arguments).

Usage:
  /path/to/venv/bin/python api_mcp/client_call_tool.py

You can override the server URL with the MCP_SERVER_URL env var, e.g.
  MCP_SERVER_URL=http://localhost:8020 /path/to/venv/bin/python api_mcp/client_call_tool.py
"""

import asyncio
import json
import os
from fastmcp.client.client import Client


async def main() -> None:
    base_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8020")
    transport_url = f"{base_url.rstrip('/')}/mcp"

    print(f"Connecting to MCP server at {transport_url}...")
    client = Client(transport_url)

    async with client:
        tools = await client.list_tools()
        print("Available tools:")
        for t in tools:
            print(" -", t.name)

        # Try to find a product-listing tool
        candidates = [t.name for t in tools if "list_products" in t.name or ("products" in t.name and "list" in t.name)]
        if not candidates:
            candidates = [t.name for t in tools if "product" in t.name or "products" in t.name]

        if not candidates:
            print("\nNo product tool found; exiting")
            return

        tool_name = candidates[0]
        print(f"\nCalling tool: {tool_name} with no args (list all products)")
        result = await client.call_tool(tool_name, {})

        data = getattr(result, "data", None) or getattr(result, "structured_content", None) or getattr(result, "content", None)
        print("\nCall result (truncated to 2000 chars):")
        print(json.dumps(data, indent=2, default=str)[:2000])


if __name__ == "__main__":
    asyncio.run(main())
