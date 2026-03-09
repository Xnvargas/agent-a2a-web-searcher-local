"""
Base factory for creating specialist agents.

Each specialist is a compiled LangGraph sub-graph with:
- Filtered tool set (only tools relevant to its scope)
- Scoped system prompt
- Agent activity logging
- Configurable model selection
"""

from typing import List, Optional

# Model constants
MODEL_REASONING = "qwen3.5:35b"                    # Orchestrator, Opp, Account, Product, Architect
MODEL_LIGHTWEIGHT = "ibm/granite4:small-h-q4_K_M"  # Document, Research


def create_specialist_agent(
    agent_name: str,
    tools: List,
    system_prompt: str,
    model: str = MODEL_REASONING,
    api_base: str = "http://192.168.0.58:11434",
    recursion_limit: int = 20,
):
    """
    Create a specialist sub-graph agent.

    Args:
        agent_name: Identifier for logging ('opportunity', 'account', etc.)
        tools: Filtered tool list - ONLY tools this agent should see
        system_prompt: Scoped prompt for this agent's role
        model: Ollama model name
        api_base: Ollama server URL
        recursion_limit: Max tool loops (tighter for specialists)

    Returns:
        Compiled LangGraph StateGraph
    """
    from utils.langgraph_factory import create_langgraph_agent

    print(f"\n  Creating specialist: {agent_name} ({len(tools)} tools, model={model})")

    return create_langgraph_agent(
        api_model=model,
        api_key="unused",
        api_base=api_base,
        tools=tools,
        system_prompt=system_prompt,
        recursion_limit=recursion_limit,
    )
