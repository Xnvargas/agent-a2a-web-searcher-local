"""
=============================================================================
UPDATE SOLUTION TOOL
=============================================================================

Update an existing solution's overview, architecture_details, or
implementation_notes. Reads the current content first so the agent can make
targeted edits without losing existing sections.

Only provided fields are changed — omitted fields are left unchanged.

=============================================================================
"""

import re
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.sql import run_query
from utils.mermaid_validator import validate_and_fix_mermaid, format_validation_summary


class UpdateSolutionTool(LangChainTool):
    """
    Update an existing solution architecture via SQLDatabase.

    Supports partial updates — only provided fields are modified.
    Includes Mermaid diagram validation and auto-fix before persisting.
    """

    name = "update_solution"
    description = (
        "Update an existing solution architecture. Can update overview, "
        "architecture_details, and/or implementation_notes independently — "
        "fields not provided are left unchanged. "
        "WARNING: Each provided field REPLACES the entire stored value. "
        "To make additive edits, first read the current content with "
        "get_solution_content(field=...), then include ALL existing content "
        "plus your changes in the parameter. Never use get_entity_details "
        "for reading solution content — it returns truncated previews."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "solution_id": {
                "type": "string",
                "required": False,
                "description": (
                    "UUID of the solution to update. If not provided, "
                    "updates the current opportunity's latest solution."
                )
            },
            "overview": {
                "type": "string",
                "required": False,
                "description": (
                    "Full replacement value for overview. WARNING: This overwrites the entire field. "
                    "To make additive edits, first read the current content with "
                    "get_solution_content(field='overview'), then include ALL existing content "
                    "plus your changes. Omit to leave unchanged."
                )
            },
            "architecture_details": {
                "type": "string",
                "required": False,
                "description": (
                    "Full replacement value for architecture_details. WARNING: This overwrites the entire field. "
                    "To make additive edits, first read the current content with "
                    "get_solution_content(field='architecture_details'), then include ALL existing content "
                    "plus your changes. Omit to leave unchanged."
                )
            },
            "implementation_notes": {
                "type": "string",
                "required": False,
                "description": (
                    "Full replacement value for implementation_notes. WARNING: This overwrites the entire field. "
                    "To make additive edits, first read the current content with "
                    "get_solution_content(field='implementation_notes'), then include ALL existing content "
                    "plus your changes. Omit to leave unchanged."
                )
            }
        }

    async def execute(
        self,
        solution_id: Optional[str] = None,
        overview: Optional[str] = None,
        architecture_details: Optional[str] = None,
        implementation_notes: Optional[str] = None
    ) -> str:
        try:
            # Resolve solution ID
            target_id = solution_id
            if not target_id:
                ctx = SWOTContext.get_current()
                if ctx and ctx.scope.solution_id:
                    target_id = ctx.scope.solution_id
                elif ctx and ctx.scope.opportunity_id:
                    # Get latest solution for this opportunity
                    result = run_query(
                        "SELECT id FROM solutions "
                        f"WHERE opportunity_id = '{ctx.scope.opportunity_id}'::uuid "
                        "ORDER BY version DESC LIMIT 1"
                    )
                    if result and result.strip() and result.strip() != '[]':
                        uuid_match = re.search(
                            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                            result
                        )
                        if uuid_match:
                            target_id = uuid_match.group(0)

            if not target_id:
                return (
                    "No solution found to update. No solution_id was provided, "
                    "none exists in the current context, and no solution is linked "
                    "to the current opportunity. Use create_solution_draft to create one first."
                )

            # Verify solution belongs to current opportunity (prevent cross-opp writes)
            opp_id = SWOTContext.get_opportunity_id()
            if opp_id and target_id:
                verify_result = run_query(
                    f"SELECT opportunity_id FROM solutions WHERE id = '{target_id}'::uuid"
                )
                if verify_result:
                    solution_opp_match = re.search(
                        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                        verify_result
                    )
                    if solution_opp_match and solution_opp_match.group(0) != opp_id:
                        wrong_opp = solution_opp_match.group(0)
                        print(
                            f"  WARNING: Solution {target_id} belongs to opportunity "
                            f"{wrong_opp}, not current opportunity {opp_id}. "
                            f"Redirecting to correct opportunity's solution."
                        )
                        # Find the correct solution for current opportunity
                        correct_result = run_query(
                            f"SELECT id FROM solutions "
                            f"WHERE opportunity_id = '{opp_id}'::uuid "
                            f"ORDER BY version DESC LIMIT 1"
                        )
                        correct_match = re.search(
                            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                            correct_result or ''
                        )
                        if correct_match:
                            target_id = correct_match.group(0)
                            print(f"  Redirected to solution {target_id} for opportunity {opp_id}")
                        else:
                            return (
                                f"Solution {target_id} belongs to a different opportunity "
                                f"({wrong_opp}), not the current one ({opp_id}). "
                                f"No solution exists for the current opportunity. "
                                f"Use create_solution_draft to create one first."
                            )

            # Validate and fix Mermaid diagrams in provided fields
            mermaid_notes = []

            if overview is not None:
                overview, overview_results = validate_and_fix_mermaid(overview.strip())
                if overview_results:
                    mermaid_notes.append(format_validation_summary(overview_results))

            if architecture_details is not None:
                architecture_details, arch_results = validate_and_fix_mermaid(
                    architecture_details.strip()
                )
                if arch_results:
                    mermaid_notes.append(format_validation_summary(arch_results))

            if implementation_notes is not None:
                implementation_notes, impl_results = validate_and_fix_mermaid(
                    implementation_notes.strip()
                )
                if impl_results:
                    mermaid_notes.append(format_validation_summary(impl_results))

            # Build SET clause dynamically (only update provided fields)
            updates = []
            if overview is not None:
                safe_overview = overview.replace("'", "''")
                updates.append(f"overview = '{safe_overview}'")
            if architecture_details is not None:
                safe_arch = architecture_details.replace("'", "''")
                updates.append(f"architecture_details = '{safe_arch}'")
            if implementation_notes is not None:
                safe_impl = implementation_notes.replace("'", "''")
                updates.append(f"implementation_notes = '{safe_impl}'")

            if not updates:
                return (
                    "No fields provided to update. Provide at least one of: "
                    "overview, architecture_details, implementation_notes."
                )

            updates.append("updated_at = NOW()")
            set_clause = ", ".join(updates)

            result = run_query(
                f"UPDATE solutions "
                f"SET {set_clause} "
                f"WHERE id = '{target_id}'::uuid "
                f"RETURNING id, version, status"
            )

            if not result or result.strip() == '' or result.strip() == '[]':
                return f"Solution not found with ID: {target_id}"

            fields_changed = []
            if overview is not None:
                fields_changed.append("overview")
            if architecture_details is not None:
                fields_changed.append("architecture_details")
            if implementation_notes is not None:
                fields_changed.append("implementation_notes")

            validation_info = ""
            if mermaid_notes:
                validation_info = "\n\n**Mermaid Validation:**\n" + "\n".join(mermaid_notes)

            return (
                f"Solution updated successfully!\n\n"
                f"- **Solution ID:** {target_id}\n"
                f"- **Fields updated:** {', '.join(fields_changed)}\n"
                f"- **Details:** {result}\n\n"
                f"The UI will reflect changes via real-time update."
                f"{validation_info}"
            )

        except Exception as e:
            return f"Error updating solution: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def update_solution(
            solution_id: Optional[str] = None,
            overview: Optional[str] = None,
            architecture_details: Optional[str] = None,
            implementation_notes: Optional[str] = None
        ) -> str:
            """Update an existing solution's fields. Only provided fields are changed."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return update_solution
