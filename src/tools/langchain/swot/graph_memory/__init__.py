"""
=============================================================================
GRAPH MEMORY TOOLS
=============================================================================

Agent tools for building and querying a persistent knowledge graph.

These tools write to BOTH:
- agent_memory_nodes (relational + pgvector) for structured queries & semantic search
- opp_tracker AGE graph (MemoryNode vertices + edges) for relationship traversal

Tool Set:
---------
- add_memory:        Create a memory node, optionally linked to an entity
- search_memory:     Semantic/filtered search across memories
- link_memories:     Create RELATES_TO or ABOUT edges in the graph
- update_memory:     Edit content, confidence, type, tags (re-embeds if content changes)
- delete_memory:     Soft-delete (is_active=false) with graph cleanup
- get_entity_memory: Graph traversal to find all memories about an entity

Placement:
----------
Place this folder at: src/tools/langchain/swot/graph_memory/
Register tools in your tool loader or agent configuration.

=============================================================================
"""

from .add_memory import AddMemoryTool
from .search_memory import SearchMemoryTool
from .link_memories import LinkMemoriesTool
from .update_memory import UpdateMemoryTool
from .delete_memory import DeleteMemoryTool
from .get_entity_memory import GetEntityMemoryTool

__all__ = [
    "AddMemoryTool",
    "SearchMemoryTool",
    "LinkMemoriesTool",
    "UpdateMemoryTool",
    "DeleteMemoryTool",
    "GetEntityMemoryTool",
]


def get_graph_memory_tools():
    """Return instances of all graph memory tools for agent registration."""
    return [
        AddMemoryTool(),
        SearchMemoryTool(),
        LinkMemoriesTool(),
        UpdateMemoryTool(),
        DeleteMemoryTool(),
        GetEntityMemoryTool(),
    ]