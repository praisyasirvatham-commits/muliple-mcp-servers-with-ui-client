#!/usr/bin/env python3
"""
LangChain demo for the MCP orchestrator tool.

This script demonstrates:
 - Directly calling the LangChain tool's synchronous `_run` method to invoke
   the orchestrator (works even if LangChain isn't installed).
 - If LangChain is installed, running a small agent using FakeListLLM to
   simulate an LLM that instructs the agent to call the orchestrator tool.

Run with the project's venv Python:
  /path/to/venv/bin/python mcp_orchestrator/langchain_demo.py
"""

import json
import sys

from mcp_orchestrator.langchain_adapter import make_mcp_orchestrator_tool


def direct_demo():
    print("=== Direct tool invocation demo ===")
    tool = make_mcp_orchestrator_tool()

    # List products
    print("\nCalling tool with 'list products'...")
    out = tool._run("list products")
    print(json.dumps(json.loads(out), indent=2))

    # Get product 1 using JSON envelope
    print("\nCalling tool with JSON envelope for get product 1...")
    envelope = json.dumps({"query": "get product 1", "args": {}})
    out2 = tool._run(envelope)
    print(json.dumps(json.loads(out2), indent=2))


def agent_demo_if_possible():
    print("\n=== LangChain agent demo (if available) ===")
    try:
        from langchain.llms.fake import FakeListLLM
        from langchain.agents import initialize_agent, AgentType
    except Exception as e:
        print("LangChain or FakeListLLM not available; skipping agent demo.")
        print("Install langchain to run the interactive agent demo: pip install langchain")
        return

    # Create the orchestrator tool
    tool = make_mcp_orchestrator_tool()

    # We'll use a FakeListLLM to simulate the agent planning to call the tool.
    # The agent expects the LLM to return an "Action" output. The sequence below:
    # 1) Return an Action asking to call MCPOrchestrator with input 'list products'
    # 2) After the tool returns, the agent will call the LLM again; respond with final answer.

    responses = [
        # For 'list products'
        "Thought: I should list products\nAction: MCPOrchestrator\nAction Input: \"list products\"",
        "Final Answer: Listed products (simulated)",
    ]

    fake_llm = FakeListLLM(responses=responses)

    agent = initialize_agent(
        tools=[tool],
        llm=fake_llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    print("Running agent.run('list products')")
    result = agent.run("list products")
    print("Agent result:\n", result)


def main():
    try:
        direct_demo()
    except Exception as e:
        print("Direct demo failed:", type(e).__name__, e)

    # Try the agent demo if langchain is installed
    agent_demo_if_possible()


if __name__ == "__main__":
    main()
