"""
=============================================================================
GET SOLUTION CONTENT TOOL
=============================================================================

Retrieve the full content of a specific solution field (overview,
architecture_details, or implementation_notes) with pagination support.

This avoids the truncation issue where run_query returns Python's default
repr for long strings in tuples, cutting off TEXT fields with '...'.

=============================================================================
"""

import re
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query
from utils.swot_context import SWOTContext


# Maximum chars to return in a single call. Agent can paginate with offset.
MAX_CHARS_PER_CALL = 12000

VALID_FIELDS = ['overview', 'architecture_details', 'implementation_notes']


class GetSolutionContentTool(LangChainTool):
    """
    Get the full content of a specific solution field.

    Use this after get_entity_details shows a solution exists but the
    content is too large to return inline. Supports offset pagination
    for very large fields.
    """

    name = "get_solution_content"
    description = (
        "Get the full content of a specific solution field "
        "(overview, architecture_details, or implementation_notes). "
        "Use this after get_entity_details shows a solution exists "
        "but the content is too large to return inline. "
        "Supports offset pagination for very large fields."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "solution_id": {
                "type": "string",
                "required": False,
                "description": (
                    "Solution UUID. Auto-resolves from context if omitted."
                )
            },
            "field": {
                "type": "string",
                "required": True,
                "description": (
                    "Field to read: 'overview', 'architecture_details', "
                    "or 'implementation_notes'"
                )
            },
            "offset": {
                "type": "integer",
                "required": False,
                "default": 0,
                "description": "Character offset for pagination (default: 0)"
            }
        }

    async def execute(
        self,
        field: str,
        solution_id: Optional[str] = None,
        offset: int = 0,
    ) -> str:
        """Retrieve a single solution field with pagination support."""
        try:
            if field not in VALID_FIELDS:
                return f"Invalid field '{field}'. Use one of: {VALID_FIELDS}"

            target_id = solution_id or SWOTContext.get_solution_id()

            if not target_id:
                # Fallback: latest solution for current opportunity
                opp_id = SWOTContext.get_opportunity_id()
                if opp_id:
                    safe_opp = opp_id.replace("'", "''")
                    result = run_query(f"""
                        SELECT id FROM solutions
                        WHERE opportunity_id = '{safe_opp}'::uuid
                        ORDER BY version DESC LIMIT 1
                    """)
                    match = re.search(r'[0-9a-f-]{36}', result or '')
                    target_id = match.group(0) if match else None

            if not target_id:
                return "No solution found in context. Provide a solution_id."

            safe_id = target_id.replace("'", "''")
            offset = max(0, offset)

            # Get total length of the field
            length_result = run_query(f"""
                SELECT COALESCE(LENGTH({field}), 0) as field_length
                FROM solutions WHERE id = '{safe_id}'::uuid
            """)

            # Get content slice using SUBSTRING for safe pagination
            content_result = run_query(f"""
                SELECT SUBSTRING({field} FROM {offset + 1} FOR {MAX_CHARS_PER_CALL})
                FROM solutions WHERE id = '{safe_id}'::uuid
            """)

            if not content_result or content_result.strip() in ('', '[]', "[(None,)]"):
                return f"Field '{field}' is empty for solution {target_id}."

            # Parse total length from the length query result
            length_match = re.search(r'(\d+)', length_result or '0')
            total_length = int(length_match.group(1)) if length_match else 0

            # Build pagination footer
            remaining = total_length - offset - MAX_CHARS_PER_CALL
            if remaining > 0:
                footer = (
                    f"\n\nShowing {MAX_CHARS_PER_CALL} of {total_length} chars "
                    f"(offset {offset}). {remaining} remaining. "
                    f"Call again with offset={offset + MAX_CHARS_PER_CALL}."
                )
            else:
                footer = f"\n\nEnd of field. Total: {total_length} chars."

            return f"Solution {field}:\n{content_result}{footer}"

        except Exception as e:
            return f"Error retrieving solution content: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def get_solution_content(
            field: str,
            solution_id: Optional[str] = None,
            offset: int = 0,
        ) -> str:
            """Get full content of a solution field. Supports offset pagination."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_solution_content
