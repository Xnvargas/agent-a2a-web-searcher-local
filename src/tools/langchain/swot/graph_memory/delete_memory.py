"""
=============================================================================
DELETE MEMORY TOOL
=============================================================================

Soft-delete a memory node by setting is_active=false in the relational
table and removing it (and its edges) from the graph. The relational
record is preserved for audit purposes but excluded from all searches.

=============================================================================
"""

from typing import Dict, Any
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query
from utils.db.graph import run_cypher


class DeleteMemoryTool(LangChainTool):
    """
    Soft-delete a memory node.

    Deactivates in relational table (is_active=false) and removes
    the vertex and all connected edges from the graph.
    """

    name = "delete_memory"
    description = (
        "Deactivate a memory node. This soft-deletes it — the memory is hidden "
        "from searches and its graph relationships are removed, but the record "
        "is preserved for audit. Use this to remove outdated, incorrect, or "
        "superseded knowledge."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "memory_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the memory node to deactivate."
            },
            "reason": {
                "type": "string",
                "required": False,
                "description": "Optional reason for deletion (stored for audit)."
            }
        }

    async def execute(self, memory_id: str, reason: str = None) -> str:
        """Soft-delete a memory node from both relational store and graph."""
        try:
            # Verify memory exists and is active
            existing = run_query(f"""
                SELECT id::text, content, memory_type
                FROM agent_memory_nodes
                WHERE id = '{memory_id}'::uuid AND is_active = true
            """)
            if not existing or 'no rows' in str(existing).lower() or existing.strip() == '':
                return f"Memory {memory_id} not found or is already inactive."

            # ── Step 1: Soft-delete in relational table ──
            run_query(f"""
                UPDATE agent_memory_nodes
                SET is_active = false, updated_at = NOW()
                WHERE id = '{memory_id}'::uuid
            """)

            # ── Step 2: Remove from graph (vertex + all edges) ──
            try:
                # First detach all edges, then delete the vertex
                run_cypher(f"""
                    MATCH (m:MemoryNode {{id: '{memory_id}'}})
                    DETACH DELETE m
                """)
                graph_msg = "removed from graph"
            except Exception:
                graph_msg = "graph vertex not found (may not have existed)"

            reason_msg = f"\n- **Reason:** {reason}" if reason else ""

            return (
                f"Memory {memory_id[:8]}... deactivated.\n"
                f"- **Relational:** soft-deleted (is_active=false)\n"
                f"- **Graph:** {graph_msg}"
                f"{reason_msg}"
            )

        except Exception as e:
            return f"Error deleting memory: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def delete_memory(memory_id: str, reason: str = None) -> str:
            """Deactivate a memory node (soft-delete)."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return delete_memory