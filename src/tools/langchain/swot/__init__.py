"""
=============================================================================
SWOT TOOLS PACKAGE - Solution Workshop & Opportunity Tracker Tools
=============================================================================

Context-aware tools for the SWOT application. Each tool:
1. Extends LangChainTool (follows existing pattern)
2. Registers via ToolRegistry (auto-discovered by agent)
3. Uses SWOTContext for automatic scope filtering

TOOLS:
------
- search_documents: Semantic document search with entity filtering
- find_similar_solutions: Find past solutions matching a use case
- get_current_context: Get details about current page context
- get_technology_footprint: Get IBM tech deployed at an account
- query_coverage: Find who covers a product for an account
- create_solution_draft: Create a new solution architecture
- create_document_artifact: Create and save generated content

=============================================================================
"""

from tools.registry import ToolRegistry

# Import tool classes
from .search_documents import SearchDocumentsTool
from .find_similar_solutions import FindSimilarSolutionsTool
from .get_current_context import GetCurrentContextTool
from .get_technology_footprint import GetTechnologyFootprintTool
from .query_coverage import QueryCoverageTool
from .create_solution_draft import CreateSolutionDraftTool
from .create_document_artifact import CreateDocumentArtifactTool

# Register all tools with the registry
# These will be auto-discovered when get_all_tools() is called
ToolRegistry.register(SearchDocumentsTool())
ToolRegistry.register(FindSimilarSolutionsTool())
ToolRegistry.register(GetCurrentContextTool())
ToolRegistry.register(GetTechnologyFootprintTool())
ToolRegistry.register(QueryCoverageTool())
ToolRegistry.register(CreateSolutionDraftTool())
ToolRegistry.register(CreateDocumentArtifactTool())

print(f"SWOT Tools registered: 7 tools")

__all__ = [
    'SearchDocumentsTool',
    'FindSimilarSolutionsTool',
    'GetCurrentContextTool',
    'GetTechnologyFootprintTool',
    'QueryCoverageTool',
    'CreateSolutionDraftTool',
    'CreateDocumentArtifactTool',
]
