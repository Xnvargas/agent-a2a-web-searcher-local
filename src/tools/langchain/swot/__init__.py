"""
=============================================================================
SWOT TOOLS PACKAGE - Solution Workshop & Opportunity Tracker Tools
=============================================================================

Context-aware tools for the SWOT application. Each tool:
1. Extends LangChainTool (follows existing pattern)
2. Registers via ToolRegistry (auto-discovered by agent)
3. Uses SWOTContext for automatic scope filtering

TOOLS (10 total):
-----------------

Context:
- get_current_context: Get details about current page context

Vector (OllamaEmbeddings + SQLDatabase):
- search_documents: Semantic document search with entity filtering
- find_similar_solutions: Find past solutions matching a use case

Graph (AGEGraph):
- get_technology_footprint: Get IBM tech deployed at an account
- query_coverage: Find who covers a product for an account
- explore_relationships: Flexible graph exploration (NEW)

Relational (SQLDatabase):
- query_entities: Search accounts, opportunities, products (NEW)
- get_entity_details: Get full entity details by ID (NEW)
- create_solution_draft: Create a new solution architecture
- create_document_artifact: Create and save generated content

=============================================================================
"""

from tools.registry import ToolRegistry

# Context tools (no external calls — reads SWOTContext)
from .context.get_current_context import GetCurrentContextTool

# Vector tools (OllamaEmbeddings + SQLDatabase → pgvector)
from .vector.search_documents import SearchDocumentsTool
from .vector.find_similar_solutions import FindSimilarSolutionsTool

# Graph tools (AGEGraph → Apache AGE Cypher)
from .graph.get_technology_footprint import GetTechnologyFootprintTool
from .graph.query_coverage import QueryCoverageTool
from .graph.explore_relationships import ExploreRelationshipsTool

# Relational tools (SQLDatabase → PostgreSQL)
from .relational.query_entities import QueryEntitiesTool
from .relational.get_entity_details import GetEntityDetailsTool
from .relational.create_solution_draft import CreateSolutionDraftTool
from .relational.create_document_artifact import CreateDocumentArtifactTool

# Register all tools with the registry
# These will be auto-discovered when get_all_tools() is called
ToolRegistry.register(GetCurrentContextTool())
ToolRegistry.register(SearchDocumentsTool())
ToolRegistry.register(FindSimilarSolutionsTool())
ToolRegistry.register(GetTechnologyFootprintTool())
ToolRegistry.register(QueryCoverageTool())
ToolRegistry.register(ExploreRelationshipsTool())
ToolRegistry.register(QueryEntitiesTool())
ToolRegistry.register(GetEntityDetailsTool())
ToolRegistry.register(CreateSolutionDraftTool())
ToolRegistry.register(CreateDocumentArtifactTool())

print(f"SWOT Tools registered: 10 tools (7 migrated + 3 new)")

__all__ = [
    'GetCurrentContextTool',
    'SearchDocumentsTool',
    'FindSimilarSolutionsTool',
    'GetTechnologyFootprintTool',
    'QueryCoverageTool',
    'ExploreRelationshipsTool',
    'QueryEntitiesTool',
    'GetEntityDetailsTool',
    'CreateSolutionDraftTool',
    'CreateDocumentArtifactTool',
]
