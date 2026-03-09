"""
Handoff tools for multi-agent orchestration.

Each handoff tool creates and invokes a specialist sub-graph inline,
passing scoped context and the delegated question, and returns the
specialist's text response as a string.
"""

from .handoff_to_opportunity import HandoffToOpportunityTool
from .handoff_to_account import HandoffToAccountTool
from .handoff_to_product import HandoffToProductTool
from .handoff_to_document import HandoffToDocumentTool
from .handoff_to_research import HandoffToResearchTool
from .handoff_to_architect import HandoffToArchitectTool

__all__ = [
    "HandoffToOpportunityTool",
    "HandoffToAccountTool",
    "HandoffToProductTool",
    "HandoffToDocumentTool",
    "HandoffToResearchTool",
    "HandoffToArchitectTool",
]
