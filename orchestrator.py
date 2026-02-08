#!/usr/bin/env python3
"""
Lightweight MCP orchestrator.

Discovers tools on configured MCP endpoints and selects a tool to call
based on a simple keyword scoring heuristic. Intended as a minimal adapter
you can plug into an agent orchestration pipeline. Keep this file small
and synchronous for easy integration with non-async orchestrators.

Usage:
  /path/to/venv/bin/python mcp_orchestrator/orchestrator.py "list products"

You can override the servers list by editing the SERVERS constant below.
"""

import asyncio
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from fastmcp.client.client import Client


# Configure MCP endpoints to consult. Adjust/add entries as needed.
SERVERS = [
    {"name": "local_ecommerce", "transport_url": "http://localhost:8020/mcp", "tags": ["ecommerce"]},
    {"name": "remote_gcp", "transport_url": "http://localhost:9030/mcp", "tags": ["gcp", "remote"]},
]


async def _list_tools_on_server(transport_url: str):
    async with Client(transport_url) as client:
        tools = await client.list_tools()
        return tools


async def _build_registry() -> Dict[str, Dict[str, Any]]:
    """Return a mapping tool_name -> metadata including server url and tags."""
    registry: Dict[str, Dict[str, Any]] = {}
    for s in SERVERS:
        url = s["transport_url"]
        try:
            tools = await _list_tools_on_server(url)
        except Exception:
            # Ignore unreachable servers for discovery; orchestrator can still use others
            continue

        for t in tools:
            name = t.name
            registry[name] = {
                "server": url,
                "description": getattr(t, "description", None),
                "tags": list(getattr(t, "tags", []) or []),
            }

    return registry


def _tokenize(text: str) -> List[str]:
    return [tok.lower() for tok in re.findall(r"\w+", text)]


def _score_tool_for_query(tool_name: str, meta: Dict[str, Any], query: str) -> int:
    qtokens = _tokenize(query)
    score = 0
    name_tokens = _tokenize(tool_name)
    desc = (meta.get("description") or "")
    desc_tokens = _tokenize(desc)

    for qt in qtokens:
        if qt in name_tokens:
            score += 3
        if qt in desc_tokens:
            score += 2
    # small boost if tool has ecommerce tag and query mentions product/customer/order/cart
    ecommerce_keywords = {"product", "products", "customer", "customers", "order", "cart", "analytics"}
    if any(k in qtokens for k in ecommerce_keywords) and "ecommerce" in meta.get("tags", []):
        score += 5

    return score


async def _choose_best_tool_and_call(query: str, args: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Any]:
    registry = await _build_registry()
    if not registry:
        raise RuntimeError("No MCP servers reachable or no tools discovered")

    # Score each tool
    scored: List[Tuple[int, str, Dict[str, Any]]] = []
    for name, meta in registry.items():
        sc = _score_tool_for_query(name, meta, query)
        scored.append((sc, name, meta))

    scored.sort(reverse=True, key=lambda x: x[0])

    # Pick top-scoring tool if score > 0, otherwise None
    top_score, top_name, top_meta = scored[0]
    if top_score <= 0:
        # Special-case fallback: if user asked to 'list orders' and no matching tool
        # was found via MCP, try the REST endpoint at localhost:8000/orders/ as a
        # fallback so the orchestrator can still return a list view.
        if "list" in _tokenize(query) and "order" in _tokenize(query):
            import httpx

            try:
                r = httpx.get("http://localhost:8000/orders/", timeout=2.0)
                r.raise_for_status()
                return "rest:/orders/", r.json()
            except Exception as e:
                return None, {"error": "No matching tool found", "fallback_error": str(e)}

        return None, {"error": "No matching tool found"}

    # Prepare args; default to empty object if None
    call_args = args or {}

    # Basic heuristic: if the chosen tool name mentions product_id and query contains a number, pass it
    # General heuristic: if the chosen tool name contains any '<name>_id' path parameter
    # (for example 'product_id', 'order_id', 'customer_id'), and no args were provided,
    # extract the first integer from the query and set that param.
    if isinstance(call_args, dict) and not call_args:
        # match tokens like 'order_id' or 'product_id' (avoid matching the whole name with underscores)
        id_params = re.findall(r"([a-z0-9]+_id)", top_name, flags=re.IGNORECASE)
        if id_params:
            m = re.search(r"\b(\d+)\b", query)
            if m:
                # prefer the first id-like param if multiple are present
                call_args[id_params[0]] = int(m.group(1))

    # Heuristic for simple arithmetic tools (add/subtract): extract two numbers from the query
    if any(k in top_name for k in ("add", "subtract")) and isinstance(call_args, dict) and not call_args:
        nums = re.findall(r"\b-?\d+(?:\.\d+)?\b", query)
        if len(nums) >= 2:
            def _parse_num(s: str):
                return int(s) if s.isdigit() or (s.startswith('-') and s[1:].isdigit()) else float(s)

            call_args["a"] = _parse_num(nums[0])
            call_args["b"] = _parse_num(nums[1])

    # Call the tool on its server
    server_url = top_meta["server"]
    # DEBUG: show the chosen tool and args we'll send
    print("DEBUG: calling tool=", top_name, "on", server_url, "with args=", call_args)
    async with Client(server_url) as client:
        result = await client.call_tool(top_name, call_args)

    # Extract preferred structured content
    content = getattr(result, "data", None) or getattr(result, "structured_content", None) or getattr(result, "content", None)
    return top_name, content


def choose_and_call(query: str, args: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Any]:
    return asyncio.run(_choose_best_tool_and_call(query, args=args))


async def choose_and_call_async(query: str, args: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Any]:
    """Async entrypoint usable from async frameworks (FastAPI handlers).

    Use this when already running inside an event loop instead of calling
    asyncio.run() which raises if an event loop is active.
    """
    return await _choose_best_tool_and_call(query, args=args)


def _cli_main():
    if len(sys.argv) < 2:
        print("Usage: orchestrator.py \"natural language query\" [json-args]")
        sys.exit(2)

    query = sys.argv[1]
    args = None
    if len(sys.argv) > 2:
        try:
            args = json.loads(sys.argv[2])
        except Exception as e:
            print("Failed to parse json args:", e)
            sys.exit(2)

    tool_name, result = choose_and_call(query, args=args)
    print("Selected tool:", tool_name)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    _cli_main()
