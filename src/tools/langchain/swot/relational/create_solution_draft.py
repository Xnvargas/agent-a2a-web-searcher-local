"""
=============================================================================
CREATE SOLUTION DRAFT TOOL
=============================================================================

Create a new solution architecture draft linked to an opportunity.
Migrated from httpx HTTP proxy to direct SQLDatabase INSERT.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.sql import run_query
from utils.mermaid_validator import validate_and_fix_mermaid, format_validation_summary


class CreateSolutionDraftTool(LangChainTool):
    """
    Create a new solution architecture draft via SQLDatabase.

    Automatically links to current opportunity if in opportunity context.
    Creates a new version if a solution already exists.
    """

    name = "create_solution_draft"
    description = (
        "REQUIRED: Use this tool whenever the user asks to create, draft, or design "
        "a solution architecture. This saves the architecture to the database so it "
        "appears in the opportunity's Solution Architecture section in the UI. "
        "Do NOT just describe architectures in chat text — always persist using this tool. "
        "Both overview and architecture_details support full markdown including "
        "Mermaid diagrams (```mermaid fenced code blocks). "
        "Automatically links to the current opportunity. If a solution already "
        "exists, this creates a new version."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "overview": {
                "type": "string",
                "required": True,
                "description": "High-level solution overview describing the approach"
            },
            "architecture_details": {
                "type": "string",
                "required": False,
                "description": "Detailed architecture description, components, integrations (optional)"
            },
            "opportunity_id": {
                "type": "string",
                "required": False,
                "description": "Opportunity UUID. If not provided, uses current context."
            }
        }

    async def execute(
        self,
        overview: str,
        architecture_details: Optional[str] = None,
        opportunity_id: Optional[str] = None
    ) -> str:
        """Create a solution draft via direct SQLDatabase INSERT."""
        try:
            # Validate overview
            if not overview or len(overview.strip()) < 10:
                return "Please provide a meaningful solution overview (at least 10 characters)."

            # Resolve opportunity ID
            target_opp = opportunity_id or SWOTContext.get_opportunity_id()
            if not target_opp:
                return (
                    "No opportunity_id provided and none available in current context. "
                    "Cannot create a solution without linking to an opportunity. "
                    "Please specify an opportunity_id or navigate to an opportunity page."
                )

            # Validate and fix Mermaid diagrams before persisting
            mermaid_notes = []
            validated_overview = overview.strip()
            validated_arch = architecture_details.strip() if architecture_details else None

            validated_overview, overview_results = validate_and_fix_mermaid(validated_overview)
            if overview_results:
                mermaid_notes.append(format_validation_summary(overview_results))

            if validated_arch:
                validated_arch, arch_results = validate_and_fix_mermaid(validated_arch)
                if arch_results:
                    mermaid_notes.append(format_validation_summary(arch_results))

            # Escape single quotes in content
            safe_overview = validated_overview.replace("'", "''")
            safe_arch = validated_arch.replace("'", "''") if validated_arch else None

            arch_value = f"'{safe_arch}'" if safe_arch else "NULL"

            # Direct SQL INSERT via LangChain SQLDatabase
            result = run_query(f"""
                INSERT INTO solutions (opportunity_id, overview, architecture_details, status, version)
                VALUES (
                    '{target_opp}'::uuid,
                    '{safe_overview}',
                    {arch_value},
                    'draft',
                    COALESCE((SELECT MAX(version) FROM solutions WHERE opportunity_id = '{target_opp}'::uuid), 0) + 1
                )
                RETURNING id, version, status
            """)

            # Get opportunity name from context for confirmation
            ctx = SWOTContext.get_current()
            opp_name = ctx.summary.entity_name if ctx else "the opportunity"

            validation_info = ""
            if mermaid_notes:
                validation_info = "\n\n**Mermaid Validation:**\n" + "\n".join(mermaid_notes)

            return (
                f"Solution draft created successfully!\n\n"
                f"- **Linked to:** {opp_name}\n"
                f"- **Status:** Draft\n"
                f"- **Details:** {result}\n\n"
                f"Overview saved:\n{overview[:200]}{'...' if len(overview) > 200 else ''}"
                f"{validation_info}"
            )

        except Exception as e:
            return f"Error creating solution: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def create_solution_draft(
            overview: str,
            architecture_details: Optional[str] = None,
            opportunity_id: Optional[str] = None
        ) -> str:
            """Create a new solution architecture draft linked to an opportunity."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return create_solution_draft
