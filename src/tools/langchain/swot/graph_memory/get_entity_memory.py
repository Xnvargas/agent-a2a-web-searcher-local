"""
=============================================================================
GET ENTITY MEMORY TOOL
=============================================================================

Retrieve all memories linked to a specific entity via graph traversal.
Uses AGE Cypher to follow ABOUT edges from MemoryNodes to entities,
and optionally traverses RELATES_TO chains to find transitively
connected memories.

This is the "pull" complement to add_memory's "push" — given an entity,
surface everything the agent knows about it.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.graph import run_cypher
from utils.db.sql import run_query


class GetEntityMemoryTool(LangChainTool):
    """
    Retrieve all memories associated with an entity via graph traversal.

    Supports:
    - Direct ABOUT relationships (memory → entity)
    - Transitive discovery via RELATES_TO chains (memory → memory → entity)
    - Filtering by memory type
    - Enrichment with relational data (confidence, timestamps)
    """

    name = "get_entity_memory"
    description = (
        "Retrieve all memories linked to a specific entity (opportunity, account, "
        "product, etc.). Traverses the knowledge graph to find directly linked "
        "memories and optionally discovers transitively connected memories through "
        "RELATES_TO chains. Use this to build a complete picture of what the agent "
        "knows about any business entity."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "entity_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the entity to retrieve memories for."
            },
            "entity_type": {
                "type": "string",
                "required": True,
                "description": (
                    "Entity type: 'opportunity', 'account', 'product', "
                    "'solution', 'document', 'team_member'"
                )
            },
            "memory_type": {
                "type": "string",
                "required": False,
                "description": "Filter by memory type: 'fact', 'insight', 'decision', etc."
            },
            "include_related": {
                "type": "boolean",
                "required": False,
                "description": (
                    "If true, also returns memories connected via RELATES_TO chains "
                    "(up to 2 hops). Default: false."
                )
            },
            "limit": {
                "type": "integer",
                "required": False,
                "description": "Max results. Default: 20."
            }
        }

    async def execute(
        self,
        entity_id: str,
        entity_type: str,
        memory_type: Optional[str] = None,
        include_related: Optional[bool] = False,
        limit: Optional[int] = None,
    ) -> str:
        """Retrieve memories linked to an entity via graph traversal."""
        try:
            max_results = min(limit or 20, 50)

            label_map = {
                'opportunity': 'Opportunity',
                'account': 'Account',
                'product': 'Product',
                'solution': 'Solution',
                'document': 'Document',
                'team_member': 'TeamMember',
            }
            graph_label = label_map.get(entity_type)
            if not graph_label:
                return f"Invalid entity type '{entity_type}'. Options: {', '.join(sorted(label_map.keys()))}"

            # ── Step 1: Direct memories (ABOUT edges) ──
            type_filter = f" AND m.memory_type = '{memory_type}'" if memory_type else ""

            try:
                direct_results = run_cypher(f"""
                    MATCH (m:MemoryNode)-[:ABOUT]->(e:{graph_label} {{id: '{entity_id}'}})
                    WHERE m.is_active = 'true'{type_filter}
                    RETURN m.id AS id, m.memory_type AS memory_type, m.content AS content, 
                           m.confidence AS confidence, m.tags AS tags
                    LIMIT {max_results}
                """)
            except Exception:
                direct_results = []

            # ── Step 2: Transitive memories via RELATES_TO (optional) ──
            related_results = []
            if include_related and direct_results:
                # Get IDs of direct memories to traverse from
                direct_ids = [r.get('id', '') for r in direct_results if r.get('id')]
                if direct_ids:
                    for mem_id in direct_ids[:5]:  # Limit traversal starts
                        try:
                            related = run_cypher(f"""
                                MATCH (origin:MemoryNode {{id: '{mem_id}'}})-[r:RELATES_TO*1..2]-(connected:MemoryNode)
                                WHERE connected.is_active = 'true'{type_filter}
                                  AND connected.id <> '{mem_id}'
                                RETURN DISTINCT connected.id AS id, connected.memory_type AS memory_type,
                                       connected.content AS content, connected.confidence AS confidence,
                                       connected.tags AS tags
                                LIMIT 5
                            """)
                            related_results.extend(related)
                        except Exception:
                            continue

            # ── Step 3: Enrich with relational data ──
            all_memories = direct_results.copy()

            # Deduplicate related results
            direct_ids_set = {r.get('id', '') for r in direct_results}
            for r in related_results:
                if r.get('id', '') not in direct_ids_set:
                    all_memories.append(r)
                    direct_ids_set.add(r.get('id', ''))

            if not all_memories:
                # Fall back to relational query (memories might not be in graph yet)
                type_clause = f"AND memory_type = '{memory_type}'" if memory_type else ""
                fallback = run_query(f"""
                    SELECT id::text, memory_type, content, confidence, created_at::text
                    FROM agent_memory_nodes
                    WHERE related_entity_type = '{entity_type}'
                      AND related_entity_id = '{entity_id}'::uuid
                      AND is_active = true
                      {type_clause}
                    ORDER BY created_at DESC
                    LIMIT {max_results}
                """)

                if not fallback or fallback.strip() == '' or 'no rows' in fallback.lower():
                    return f"No memories found linked to {entity_type} ({entity_id[:8]}...)."

                return (
                    f"Memories for {entity_type} ({entity_id[:8]}...):\n"
                    f"(from relational store — graph edges may need syncing)\n\n{fallback}"
                )

            # ── Step 4: Format output ──
            lines = [f"Memories for {entity_type} ({entity_id[:8]}...):\n"]

            # Direct memories
            if direct_results:
                lines.append(f"**Direct memories ({len(direct_results)}):**\n")
                for r in direct_results:
                    mem_type = r.get('memory_type', 'unknown')
                    content = r.get('content', '')
                    conf = r.get('confidence', '?')
                    mem_id = r.get('id', '?')
                    tags = r.get('tags', '')
                    preview = str(content)[:150] + ('...' if len(str(content)) > 150 else '')
                    tag_str = f" [{tags}]" if tags else ""
                    lines.append(
                        f"- **[{mem_type}]** (confidence: {conf}){tag_str}\n"
                        f"  {preview}\n"
                        f"  _ID: {mem_id}_"
                    )

            # Related memories (via RELATES_TO)
            related_only = [r for r in all_memories if r.get('id', '') not in 
                          {m.get('id', '') for m in direct_results}]
            if related_only:
                lines.append(f"\n**Related memories ({len(related_only)}, via RELATES_TO):**\n")
                for r in related_only:
                    mem_type = r.get('memory_type', 'unknown')
                    content = r.get('content', '')
                    mem_id = r.get('id', '?')
                    preview = str(content)[:150] + ('...' if len(str(content)) > 150 else '')
                    lines.append(
                        f"- **[{mem_type}]** {preview}\n"
                        f"  _ID: {mem_id}_"
                    )

            lines.append(f"\n**Total:** {len(all_memories)} memories")
            return '\n'.join(lines)

        except Exception as e:
            return f"Error retrieving entity memory: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def get_entity_memory(
            entity_id: str,
            entity_type: str,
            memory_type: Optional[str] = None,
            include_related: Optional[bool] = False,
            limit: Optional[int] = None,
        ) -> str:
            """Retrieve all memories linked to a specific entity."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_entity_memory