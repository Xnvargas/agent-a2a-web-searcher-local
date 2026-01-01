"""
=============================================================================
AGENTSTACK AGENTS PACKAGE
=============================================================================

This package contains the agent implementations:

1. LangGraph Agent (agent.py):
   - Uses LangGraph for orchestration
   - StateGraph-based execution
   - Default port: 8005

2. BeeAI Framework Agent (bee_agent.py):
   - Uses BeeAI Framework's RequirementAgent
   - Declarative requirements-based execution
   - Default port: 8006

Both agents share the same tools from the tools/ package.

To run the LangGraph agent:
    python -m agentstack_agents.agent
    or
    server (from pyproject.toml script)

To run the BeeAI agent:
    python -m agentstack_agents.bee_agent
    or
    BEE_PORT=8006 python -m agentstack_agents.bee_agent

=============================================================================
"""

# LangGraph Agent
from .agent import run, granite_4_starter

# BeeAI Framework Agent
from .bee_agent import (
    run as bee_run,
    bee_granite_4_starter,
    bee_server,
)

__all__ = [
    # LangGraph Agent
    "run",
    "granite_4_starter",
    
    # BeeAI Framework Agent
    "bee_run",
    "bee_granite_4_starter",
    "bee_server",
]
