"""
=============================================================================
ADD MEMORY TOOL
=============================================================================

Create a memory node in both the relational table (agent_memory_nodes) and
the AGE graph (MemoryNode vertex). Optionally links it to an entity via
an ABOUT edge.

Dual-write ensures:
- Relational: structured queries, vector similarity, confidence tracking
- Graph: relationship traversal across memories and entities

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query
from utils.db.graph import run_cypher
from utils.db.embeddings import generate_embedding


class AddMemoryTool(LangChainTool):
    """
    Create a new memory node with optional entity linkage.

    Writes to both:
    - agent_memory_nodes (relational + vector embedding)
    - opp_tracker graph (MemoryNode vertex + optional ABOUT edge)
    """

    name = "add_memory"
    description = (
        "Store a new piece of knowledge or insight as a memory node. "
        "Memory types: 'fact' (verified information), 'insight' (analysis or inference), "
        "'decision' (choices made), 'preference' (client/user preferences), "
        "'context' (background information), 'action_item' (follow-ups needed). "
        "Optionally link to an entity (opportunity, account, product, solution, document). "
        "Use this to build a persistent knowledge graph the agent can query later."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "content": {
                "type": "string",
                "required": True,
                "description": "The memory content — a clear, self-contained statement of knowledge."
            },
            "memory_type": {
                "type": "string",
                "required": True,
                "description": (
                    "Type of memory: 'fact', 'insight', 'decision', 'preference', "
                    "'context', or 'action_item'"
                )
            },
            "confidence": {
                "type": "number",
                "required": False,
                "description": "Confidence score 0.0-1.0 (default 1.0). Use lower values for inferences."
            },
            "related_entity_type": {
                "type": "string",
                "required": False,
                "description": (
                    "Entity type to link this memory to: 'opportunity', 'account', "
                    "'product', 'solution', 'document', 'team_member'"
                )
            },
            "related_entity_id": {
                "type": "string",
                "required": False,
                "description": "UUID of the entity to link this memory to."
            },
            "tags": {
                "type": "string",
                "required": False,
                "description": "Comma-separated tags for categorization (e.g., 'technical,architecture,risk')."
            }
        }

    async def execute(
        self,
        content: str,
        memory_type: str,
        confidence: Optional[float] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> str:
        """Create a memory node in both relational store and graph."""
        try:
            # Validate memory_type
            valid_types = {'fact', 'insight', 'decision', 'preference', 'context', 'action_item'}
            if memory_type not in valid_types:
                return f"Invalid memory_type '{memory_type}'. Must be one of: {', '.join(sorted(valid_types))}"

            # Validate content
            if not content or len(content.strip()) < 5:
                return "Memory content must be at least 5 characters."

            # Validate confidence
            conf = confidence if confidence is not None else 1.0
            if not (0.0 <= conf <= 1.0):
                return "Confidence must be between 0.0 and 1.0."

            # Validate entity linkage (both or neither)
            if bool(related_entity_type) != bool(related_entity_id):
                return "Both related_entity_type and related_entity_id must be provided together."

            valid_entity_types = {
                'opportunity', 'account', 'product', 'solution', 'document', 'team_member'
            }
            if related_entity_type and related_entity_type not in valid_entity_types:
                return f"Invalid entity type '{related_entity_type}'. Must be one of: {', '.join(sorted(valid_entity_types))}"

            # ── Step 1: Generate embedding ──
            embedding = await generate_embedding(content)
            embedding_str = f"[{','.join(str(x) for x in embedding)}]"

            # ── Step 2: Insert into relational table ──
            safe_content = content.strip().replace("'", "''")
            entity_type_sql = f"'{related_entity_type}'" if related_entity_type else "NULL"
            entity_id_sql = f"'{related_entity_id}'::uuid" if related_entity_id else "NULL::uuid"

            result = run_query(f"""
                INSERT INTO agent_memory_nodes (
                    memory_type, content, confidence,
                    related_entity_type, related_entity_id,
                    embedding, is_active
                ) VALUES (
                    '{memory_type}',
                    '{safe_content}',
                    {conf},
                    {entity_type_sql},
                    {entity_id_sql},
                    '{embedding_str}'::vector,
                    true
                )
                RETURNING id::text, memory_type, created_at
            """)

            # Extract the UUID from the result
            # run_query returns a string representation
            memory_id = None
            if result:
                # Parse the ID from the result string
                import re
                id_match = re.search(
                    r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
                    str(result)
                )
                if id_match:
                    memory_id = id_match.group(1)

            if not memory_id:
                return f"Memory inserted into relational store but could not extract ID. Result: {result}"

            # ── Step 3: Create MemoryNode vertex in graph ──
            safe_content_cypher = content.strip().replace("'", "\\'").replace('"', '\\"')
            if isinstance(tags, list):
                tags_str = ','.join(str(t).strip() for t in tags)
            elif tags:
                tags_str = tags.strip()
            else:
                tags_str = "" 

            run_cypher(f"""
                CREATE (m:MemoryNode {{
                    id: '{memory_id}',
                    memory_type: '{memory_type}',
                    content: '{safe_content_cypher}',
                    confidence: '{conf}',
                    tags: '{tags_str}',
                    is_active: 'true'
                }})
                RETURN m
            """)

            # ── Step 4: Create ABOUT edge if entity is specified ──
            link_msg = ""
            if related_entity_type and related_entity_id:
                # Map entity type to graph label
                label_map = {
                    'opportunity': 'Opportunity',
                    'account': 'Account',
                    'product': 'Product',
                    'solution': 'Solution',
                    'document': 'Document',
                    'team_member': 'TeamMember',
                }
                graph_label = label_map.get(related_entity_type)

                if graph_label:
                    try:
                        run_cypher(f"""
                            MATCH (m:MemoryNode {{id: '{memory_id}'}})
                            MATCH (e:{graph_label} {{id: '{related_entity_id}'}})
                            CREATE (m)-[:ABOUT {{context: '{memory_type}'}}]->(e)
                            RETURN m
                        """)
                        link_msg = f"\n- **Linked to:** {related_entity_type} ({related_entity_id})"
                    except Exception as link_err:
                        link_msg = f"\n- **Link warning:** Could not create ABOUT edge ({link_err}). Entity may not exist in graph."

            tags_msg = f"\n- **Tags:** {tags}" if tags else ""

            return (
                f"Memory created successfully!\n\n"
                f"- **ID:** {memory_id}\n"
                f"- **Type:** {memory_type}\n"
                f"- **Confidence:** {conf}"
                f"{link_msg}{tags_msg}\n"
                f"- **Content:** {content[:200]}{'...' if len(content) > 200 else ''}"
            )

        except Exception as e:
            return f"Error creating memory: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def add_memory(
            content: str,
            memory_type: str,
            confidence: Optional[float] = None,
            related_entity_type: Optional[str] = None,
            related_entity_id: Optional[str] = None,
            tags: Optional[str] = None,
        ) -> str:
            """Store a new piece of knowledge or insight as a memory node."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return add_memory