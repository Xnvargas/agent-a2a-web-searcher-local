"""
=============================================================================
LINK MEMORIES TOOL
=============================================================================

Create relationships in the knowledge graph:
- MemoryNode ←RELATES_TO→ MemoryNode (with labeled relationship type)
- MemoryNode ←ABOUT→ Entity (link memory to any entity node)

This enables the agent to build rich associative networks of knowledge
that can be traversed to understand how insights connect to business
entities and to each other.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.graph import run_cypher
from utils.db.sql import run_query


class LinkMemoriesTool(LangChainTool):
    """
    Create relationships between memory nodes and/or entities in the graph.

    Supports two link types:
    - memory_to_memory: RELATES_TO edge with a relationship label
    - memory_to_entity: ABOUT edge linking a memory to a business entity
    """

    name = "link_memories"
    description = (
        "Create relationships in the knowledge graph. Use 'memory_to_memory' to connect "
        "two memory nodes with a labeled relationship (e.g., supports, contradicts, extends, "
        "caused_by, follow_up, related). Use 'memory_to_entity' to link a memory to a "
        "business entity (opportunity, account, product, etc.). This builds an associative "
        "knowledge network the agent can traverse."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "link_type": {
                "type": "string",
                "required": True,
                "description": "'memory_to_memory' or 'memory_to_entity'"
            },
            "source_memory_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the source memory node."
            },
            "target_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the target (memory node or entity)."
            },
            "relationship": {
                "type": "string",
                "required": False,
                "description": (
                    "For memory_to_memory: relationship label — 'supports', 'contradicts', "
                    "'extends', 'caused_by', 'follow_up', 'related', 'supersedes'. Default: 'related'. "
                    "For memory_to_entity: optional context label for the ABOUT edge."
                )
            },
            "target_entity_type": {
                "type": "string",
                "required": False,
                "description": (
                    "Required for memory_to_entity. Entity type: 'opportunity', 'account', "
                    "'product', 'solution', 'document', 'team_member'"
                )
            }
        }

    async def execute(
        self,
        link_type: str,
        source_memory_id: str,
        target_id: str,
        relationship: Optional[str] = None,
        target_entity_type: Optional[str] = None,
    ) -> str:
        """Create a relationship in the knowledge graph."""
        try:
            if link_type not in ('memory_to_memory', 'memory_to_entity'):
                return "link_type must be 'memory_to_memory' or 'memory_to_entity'."

            # Verify source memory exists
            source_check = run_query(f"""
                SELECT id::text, content FROM agent_memory_nodes 
                WHERE id = '{source_memory_id}'::uuid AND is_active = true
            """)
            if not source_check or 'no rows' in str(source_check).lower() or source_check.strip() == '':
                return f"Source memory {source_memory_id} not found or is inactive."

            if link_type == "memory_to_memory":
                return await self._link_memory_to_memory(
                    source_memory_id, target_id, relationship or "related"
                )
            else:
                if not target_entity_type:
                    return "target_entity_type is required for memory_to_entity links."
                return await self._link_memory_to_entity(
                    source_memory_id, target_id, target_entity_type, relationship
                )

        except Exception as e:
            return f"Error creating link: {str(e)}"

    async def _link_memory_to_memory(
        self, source_id: str, target_id: str, relationship: str
    ) -> str:
        """Create a RELATES_TO edge between two MemoryNode vertices."""
        valid_relationships = {
            'supports', 'contradicts', 'extends', 'caused_by',
            'follow_up', 'related', 'supersedes', 'depends_on',
            'evidence_for', 'derived_from'
        }
        if relationship not in valid_relationships:
            return (
                f"Invalid relationship '{relationship}'. Options: "
                f"{', '.join(sorted(valid_relationships))}"
            )

        # Verify target memory exists
        target_check = run_query(f"""
            SELECT id::text FROM agent_memory_nodes 
            WHERE id = '{target_id}'::uuid AND is_active = true
        """)
        if not target_check or 'no rows' in str(target_check).lower() or target_check.strip() == '':
            return f"Target memory {target_id} not found or is inactive."

        safe_rel = relationship.replace("'", "\\'")

        run_cypher(f"""
            MATCH (s:MemoryNode {{id: '{source_id}'}})
            MATCH (t:MemoryNode {{id: '{target_id}'}})
            CREATE (s)-[:RELATES_TO {{relationship: '{safe_rel}'}}]->(t)
            RETURN s, t
        """)

        return (
            f"Link created: Memory ({source_id[:8]}...) "
            f"—[{relationship}]→ Memory ({target_id[:8]}...)"
        )

    async def _link_memory_to_entity(
        self, memory_id: str, entity_id: str, entity_type: str, context: Optional[str]
    ) -> str:
        """Create an ABOUT edge from a MemoryNode to an entity vertex."""
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

        context_prop = f", context: '{context}'" if context else ""

        try:
            run_cypher(f"""
                MATCH (m:MemoryNode {{id: '{memory_id}'}})
                MATCH (e:{graph_label} {{id: '{entity_id}'}})
                CREATE (m)-[:ABOUT {{{context_prop.lstrip(', ')}}}]->(e)
                RETURN m, e
            """)
        except Exception as e:
            if 'did not match' in str(e).lower() or 'no match' in str(e).lower():
                return (
                    f"Could not find {entity_type} with id {entity_id} in the graph. "
                    f"The entity may not have been synced to the graph yet."
                )
            raise

        # Also update the relational table to track the primary entity link
        run_query(f"""
            UPDATE agent_memory_nodes
            SET related_entity_type = '{entity_type}',
                related_entity_id = '{entity_id}'::uuid,
                updated_at = NOW()
            WHERE id = '{memory_id}'::uuid
              AND related_entity_id IS NULL
        """)

        return (
            f"Link created: Memory ({memory_id[:8]}...) "
            f"—[ABOUT]→ {entity_type} ({entity_id[:8]}...)"
        )

    def get_langchain_tool(self):
        @tool
        def link_memories(
            link_type: str,
            source_memory_id: str,
            target_id: str,
            relationship: Optional[str] = None,
            target_entity_type: Optional[str] = None,
        ) -> str:
            """Create relationships in the knowledge graph between memories and entities."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return link_memories