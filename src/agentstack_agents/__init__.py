"""
=============================================================================
AGENTSTACK AGENTS PACKAGE
=============================================================================

This package contains the BeeAI agent implementation.

Main Components:
- agent.py: Main agent handler with BeeAI server configuration

To run the agent:
    python -m agentstack_agents.agent
    or
    server (from pyproject.toml script)

=============================================================================
"""

from .agent import run, granite_4_starter

__all__ = ["run", "granite_4_starter"]
