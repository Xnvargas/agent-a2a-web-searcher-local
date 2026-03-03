"""
=============================================================================
SEARCH MEMORY TOOL
=============================================================================

Search agent memory nodes using semantic similarity (pgvector), keyword
matching, entity filters, and memory type filters. Combines relational
queries with graph context for rich results.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query
from utils.db.embeddings import generate_embedding


class SearchMemoryTool(LangChainTool):
    """
    Search memory nodes using semantic similarity and/or filters.

    Supports:
    - Semantic search via pgvector cosine similarity
    - Keyword search via ILIKE on content
    - Filter by memory_type, entity, confidence threshold
    - Combine any of the above
    """

    name = "search_memory"
    description = (
        "Search the agent's memory for relevant knowledge. Supports semantic search "
        "(finds conceptually similar memories), keyword search, and filtering by "
        "memory type or linked entity. Use this to recall previously stored facts, "
        "insights, decisions, or context about opportunities, accounts, or products."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "query": {
                "type": "string",
                "required": False,
                "description": (
                    "Natural language search query for semantic similarity. "
                    "If omitted, uses filters only."
                )
            },
            "memory_type": {
                "type": "string",
                "required": False,
                "description": (
                    "Filter by type: 'fact', 'insight', 'decision', 'preference', "
                    "'context', 'action_item'"
                )
            },
            "related_entity_type": {
                "type": "string",
                "required": False,
                "description": "Filter by linked entity type: 'opportunity', 'account', 'product', etc."
            },
            "related_entity_id": {
                "type": "string",
                "required": False,
                "description": "Filter by linked entity UUID."
            },
            "min_confidence": {
                "type": "number",
                "required": False,
                "description": "Minimum confidence threshold (0.0-1.0). Default: 0.0 (all)."
            },
            "limit": {
                "type": "integer",
                "required": False,
                "description": "Max results to return. Default: 10."
            }
        }

    async def execute(
        self,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Search memory nodes with semantic similarity and/or filters."""
        try:
            max_results = min(limit or 10, 25)
            confidence_threshold = min_confidence or 0.0

            if not query and not memory_type and not related_entity_type and not related_entity_id:
                return (
                    "Please provide at least one search parameter: "
                    "query (semantic search), memory_type, related_entity_type, or related_entity_id."
                )

            # ── Build query ──
            conditions = ["is_active = true"]
            order_clause = "ORDER BY created_at DESC"
            select_extra = ""

            # Semantic search via embedding
            if query:
                embedding = await generate_embedding(query)
                embedding_str = f"[{','.join(str(x) for x in embedding)}]"
                select_extra = f", 1 - (embedding <=> '{embedding_str}'::vector) AS similarity"
                order_clause = "ORDER BY similarity DESC"
                # Only include results above a minimum relevance
                conditions.append(f"1 - (embedding <=> '{embedding_str}'::vector) > 0.3")

            # Filter by memory type
            if memory_type:
                conditions.append(f"memory_type = '{memory_type}'")

            # Filter by entity
            if related_entity_type:
                conditions.append(f"related_entity_type = '{related_entity_type}'")
            if related_entity_id:
                conditions.append(f"related_entity_id = '{related_entity_id}'::uuid")

            # Confidence threshold
            if confidence_threshold > 0:
                conditions.append(f"confidence >= {confidence_threshold}")

            where_clause = " AND ".join(conditions)

            sql = f"""
                SELECT
                    id::text,
                    memory_type,
                    content,
                    confidence,
                    related_entity_type,
                    related_entity_id::text,
                    created_at::text
                    {select_extra}
                FROM agent_memory_nodes
                WHERE {where_clause}
                {order_clause}
                LIMIT {max_results}
            """

            result = run_query(sql)

            if not result or result.strip() == '' or 'no rows' in result.lower() or result.strip() == '[]':
                filter_desc = []
                if query:
                    filter_desc.append(f"query='{query}'")
                if memory_type:
                    filter_desc.append(f"type={memory_type}")
                if related_entity_type:
                    filter_desc.append(f"entity={related_entity_type}")
                return f"No memories found matching: {', '.join(filter_desc) or 'given criteria'}."

            return f"Memory search results:\n\n{result}"

        except Exception as e:
            return f"Error searching memory: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def search_memory(
            query: Optional[str] = None,
            memory_type: Optional[str] = None,
            related_entity_type: Optional[str] = None,
            related_entity_id: Optional[str] = None,
            min_confidence: Optional[float] = None,
            limit: Optional[int] = None,
        ) -> str:
            """Search the agent's memory for relevant knowledge."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return search_memory