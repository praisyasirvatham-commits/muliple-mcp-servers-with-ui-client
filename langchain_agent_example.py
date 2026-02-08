#!/usr/bin/env python3
"""
LangChain agent example using the MCP orchestrator tool.

This script demonstrates how to wire the `MCPOrchestrator` tool into a
LangChain agent. It uses `FakeListLLM` by default so the demo runs without
external API keys. If you want to use a real LLM, set the environment
variables or replace the `FakeListLLM` with your preferred LLM class.

Usage:
  # (install langchain first in your venv)
  '/path/to/venv/bin/python' mcp_orchestrator/langchain_agent_example.py

Requirements (for the agent demo):
  pip install langchain

This file is safe to import even if LangChain is not installed; the demo
will print a short message and exit.
"""

import json
import sys

from mcp_orchestrator.langchain_adapter import make_mcp_orchestrator_tool


def run_agent_demo():
    try:
        from langchain.llms.fake import FakeListLLM
        from langchain.agents import initialize_agent, AgentType
    except Exception:
        print("LangChain not available in this environment. To run the agent demo:")
        print("  pip install langchain")
        print("Then re-run this script with your venv python.")
        return

    # Create the MCP orchestrator tool (LangChain wrapper)
    tool = make_mcp_orchestrator_tool()

    # Fake LLM responses: first instructs the agent to call the tool,
    # second returns a final answer after the tool runs.
    responses = [
        "Thought: I should list products\nAction: MCPOrchestrator\nAction Input: \"list products\"",
        "Final Answer: Listed products (simulated)",
    ]

    llm = FakeListLLM(responses=responses)

    agent = initialize_agent(
        tools=[tool],
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    print("Running agent.run('list products')")
    answer = agent.run("list products")
    print("Agent output:\n", answer)


def main():
    # First show how to call the tool directly via the LangChain adapter
    print("=== Direct tool usage (no LangChain required) ===")
    tool = make_mcp_orchestrator_tool()
    print("Calling tool._run('list products')...")
    out = tool._run('list products')
    try:
        parsed = json.loads(out)
        print(json.dumps(parsed, indent=2))
    except Exception:
        print(out)

    # Then attempt the LangChain agent demo (FakeListLLM)
    print('\n=== LangChain agent demo (requires langchain) ===')
    run_agent_demo()


if __name__ == '__main__':
    main()
