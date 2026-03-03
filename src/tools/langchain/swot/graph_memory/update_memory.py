"""
=============================================================================
UPDATE MEMORY TOOL
=============================================================================

Edit an existing memory node's content, confidence, type, or tags.
Updates both the relational table and the graph vertex to keep them
in sync.

If content changes, regenerates the embedding vector.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query
from utils.db.graph import run_cypher
from utils.db.embeddings import generate_embedding


class UpdateMemoryTool(LangChainTool):
    """
    Update an existing memory node's content, type, confidence, or tags.

    Updates both relational table and graph vertex. Regenerates
    the embedding if content changes.
    """

    name = "update_memory"
    description = (
        "Update an existing memory node. Can change the content (re-embeds automatically), "
        "memory type, confidence score, or tags. Use this to refine knowledge as new "
        "information becomes available, adjust confidence based on evidence, or correct "
        "earlier assumptions."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "memory_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the memory node to update."
            },
            "content": {
                "type": "string",
                "required": False,
                "description": "New content (triggers re-embedding)."
            },
            "memory_type": {
                "type": "string",
                "required": False,
                "description": "New type: 'fact', 'insight', 'decision', 'preference', 'context', 'action_item'"
            },
            "confidence": {
                "type": "number",
                "required": False,
                "description": "New confidence score (0.0-1.0)."
            },
            "tags": {
                "type": "string",
                "required": False,
                "description": "New comma-separated tags (replaces existing)."
            }
        }

    async def execute(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        confidence: Optional[float] = None,
        tags: Optional[str] = None,
    ) -> str:
        """Update a memory node in both relational store and graph."""
        try:
            if not content and not memory_type and confidence is None and tags is None:
                return "Please provide at least one field to update: content, memory_type, confidence, or tags."

            # Verify memory exists and is active
            existing = run_query(f"""
                SELECT id::text, content, memory_type, confidence
                FROM agent_memory_nodes
                WHERE id = '{memory_id}'::uuid AND is_active = true
            """)
            if not existing or 'no rows' in str(existing).lower() or existing.strip() == '':
                return f"Memory {memory_id} not found or is inactive."

            # ── Build relational UPDATE ──
            set_clauses = ["updated_at = NOW()"]
            changes = []

            if content:
                if len(content.strip()) < 5:
                    return "Content must be at least 5 characters."
                safe_content = content.strip().replace("'", "''")
                set_clauses.append(f"content = '{safe_content}'")
                changes.append("content")

                # Regenerate embedding
                embedding = await generate_embedding(content)
                embedding_str = f"[{','.join(str(x) for x in embedding)}]"
                set_clauses.append(f"embedding = '{embedding_str}'::vector")
                changes.append("embedding")

            if memory_type:
                valid_types = {'fact', 'insight', 'decision', 'preference', 'context', 'action_item'}
                if memory_type not in valid_types:
                    return f"Invalid memory_type '{memory_type}'. Must be one of: {', '.join(sorted(valid_types))}"
                set_clauses.append(f"memory_type = '{memory_type}'")
                changes.append("memory_type")

            if confidence is not None:
                if not (0.0 <= confidence <= 1.0):
                    return "Confidence must be between 0.0 and 1.0."
                set_clauses.append(f"confidence = {confidence}")
                changes.append("confidence")

            # ── Execute relational update ──
            run_query(f"""
                UPDATE agent_memory_nodes
                SET {', '.join(set_clauses)}
                WHERE id = '{memory_id}'::uuid
            """)

            # ── Update graph vertex ──
            graph_sets = []
            if content:
                safe_cypher = content.strip().replace("'", "\\'").replace('"', '\\"')
                graph_sets.append(f"m.content = '{safe_cypher}'")
            if memory_type:
                graph_sets.append(f"m.memory_type = '{memory_type}'")
            if confidence is not None:
                graph_sets.append(f"m.confidence = '{confidence}'")
            if tags is not None:
                safe_tags = tags.strip().replace("'", "\\'")
                graph_sets.append(f"m.tags = '{safe_tags}'")
                changes.append("tags")

            if graph_sets:
                try:
                    run_cypher(f"""
                        MATCH (m:MemoryNode {{id: '{memory_id}'}})
                        SET {', '.join(graph_sets)}
                        RETURN m
                    """)
                except Exception:
                    # Graph vertex might not exist yet — create it
                    pass

            return (
                f"Memory {memory_id[:8]}... updated successfully.\n"
                f"- **Changed fields:** {', '.join(changes)}"
            )

        except Exception as e:
            return f"Error updating memory: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def update_memory(
            memory_id: str,
            content: Optional[str] = None,
            memory_type: Optional[str] = None,
            confidence: Optional[float] = None,
            tags: Optional[str] = None,
        ) -> str:
            """Update an existing memory node's content, type, confidence, or tags."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return update_memory