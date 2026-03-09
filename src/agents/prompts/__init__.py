"""
Scoped system prompts for each specialist agent.

Each module exports a build_*_prompt(swot_context) function
that returns a focused system prompt for that agent's role.
"""

from .orchestrator_prompt import build_orchestrator_prompt
from .opportunity_prompt import build_opportunity_prompt
from .account_prompt import build_account_prompt
from .product_prompt import build_product_prompt
from .document_prompt import build_document_prompt
from .research_prompt import build_research_prompt
from .architect_prompt import build_architect_prompt

__all__ = [
    "build_orchestrator_prompt",
    "build_opportunity_prompt",
    "build_account_prompt",
    "build_product_prompt",
    "build_document_prompt",
    "build_research_prompt",
    "build_architect_prompt",
]
