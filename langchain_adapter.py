"""
LangChain adapter for the MCP orchestrator.

This module exposes a single LangChain-compatible tool that accepts a
natural-language instruction and uses the orchestrator to select and call
the appropriate MCP tool. The adapter is intentionally lightweight and
defensive: if LangChain is not installed, importing this module will
still succeed, but attempting to use the tool will raise a clear error.

Usage (LangChain agent):
  from mcp_orchestrator.langchain_adapter import make_mcp_orchestrator_tool
  tool = make_mcp_orchestrator_tool(name="MCPOrchestrator", description="Call MCP tools via orchestrator")
  agent = initialize_agent([tool], ...)

The agent should pass a short natural language instruction as the tool
input, for example: "list products" or "get product 1". The adapter
will return the orchestrator's structured JSON result as a string.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp_orchestrator.orchestrator import choose_and_call

try:
    # LangChain v0.0+ exposes BaseTool under langchain.tools
    from langchain.tools import BaseTool
except Exception:  # pragma: no cover - allow imports without langchain installed
    class BaseTool:  # type: ignore
        """Fallback BaseTool when langchain isn't installed.

        Instances will raise a friendly error when used.
        """

        name: str = "mcp_orchestrator_tool"
        description: str = "LangChain MCP orchestrator tool (requires langchain)"

        def _run(self, *args, **kwargs):
            raise RuntimeError(
                "langchain is not installed in this environment. Install it to use the LangChain adapter."
            )

        async def _arun(self, *args, **kwargs):
            raise RuntimeError(
                "langchain is not installed in this environment. Install it to use the LangChain adapter."
            )


class MCPOrchestratorTool(BaseTool):
    """A LangChain tool that forwards natural language queries to the orchestrator.

    The tool expects the agent to pass a single string argument which is the
    natural language instruction. Optionally the agent can pass a JSON string
    object as the second argument to provide explicit args that the orchestrator
    will forward to the chosen MCP tool.
    """

    name: str = "MCPOrchestrator"
    description: str = (
        "Route natural-language requests to configured MCP servers and invoke the best matching tool. "
        "Input: natural language string or JSON string. Output: JSON stringified tool result."
    )

    def _run(self, input_str: str) -> str:
        # Accept input as either a raw query or a JSON array [query, args]
        query = input_str
        args = None
        # Try to parse JSON envelope where agent passes {"query":..., "args":...}
        try:
            parsed = json.loads(input_str)
            if isinstance(parsed, dict) and "query" in parsed:
                query = parsed.get("query")
                args = parsed.get("args")
        except Exception:
            # input is plain string
            pass

        # Delegate to orchestrator (synchronous wrapper)
        tool_name, result = choose_and_call(query, args=args)

        out = {"selected_tool": tool_name, "result": result}
        return json.dumps(out, default=str)

    async def _arun(self, input_str: str) -> str:  # pragma: no cover - used by async agents
        # For async agents we'll run the sync wrapper in a thread loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run, input_str)


def make_mcp_orchestrator_tool(name: str = "MCPOrchestrator", description: str | None = None) -> BaseTool:
    """Factory returning a LangChain-compatible tool instance.

    If LangChain is not installed, the returned object will raise an informative
    RuntimeError when invoked.
    """

    tool = MCPOrchestratorTool()
    tool.name = name
    if description:
        tool.description = description
    return tool
