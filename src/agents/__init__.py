"""
Multi-Agent Team for SWOT.

Agent topology:
  Orchestrator -> Opportunity -> Account -> Product -> Document
                                                    -> Research
               -> Architect (stateful, TODO-driven)
"""

from .orchestrator import create_orchestrator

__all__ = ["create_orchestrator"]
