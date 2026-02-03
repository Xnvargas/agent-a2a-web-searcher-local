"""
=============================================================================
CREATE SOLUTION DRAFT TOOL
=============================================================================

Create a new solution architecture draft linked to an opportunity.

=============================================================================
"""

import os
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class CreateSolutionDraftTool(LangChainTool):
    """
    Create a new solution architecture draft.

    Automatically links to current opportunity if in opportunity context.
    Creates a new version if a solution already exists.
    """

    name = "create_solution_draft"
    description = (
        "Create a new solution architecture draft. Automatically links to the "
        "current opportunity if viewing one. Use this to save solution ideas, "
        "architecture overviews, and technical approaches. If a solution already "
        "exists, this creates a new version."
    )

    api_base_url: str = os.getenv("SWOT_API_BASE", "http://localhost:3000")
    timeout: float = 30.0

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
        """Create a solution draft."""
        try:
            # Validate overview
            if not overview or len(overview.strip()) < 10:
                return "Please provide a meaningful solution overview (at least 10 characters)."

            # Resolve opportunity ID
            target_opp = opportunity_id
            if not target_opp:
                target_opp = SWOTContext.get_opportunity_id()

            if not target_opp:
                return (
                    "No opportunity_id provided and none available in current context. "
                    "Cannot create a solution without linking to an opportunity. "
                    "Please specify an opportunity_id or navigate to an opportunity page."
                )

            # Build request
            payload: Dict[str, Any] = {
                "opportunityId": target_opp,
                "overview": overview.strip()
            }
            if architecture_details:
                payload["architectureDetails"] = architecture_details.strip()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/solutions",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            solution_id = data.get('id', 'unknown')
            version = data.get('version', 1)

            # Get opportunity name from context for confirmation
            ctx = SWOTContext.get_current()
            opp_name = ctx.summary.entity_name if ctx else "the opportunity"

            return (
                f"Solution draft created successfully!\n\n"
                f"- **Solution ID:** {solution_id}\n"
                f"- **Version:** {version}\n"
                f"- **Linked to:** {opp_name}\n"
                f"- **Status:** Draft\n\n"
                f"Overview saved:\n{overview[:200]}{'...' if len(overview) > 200 else ''}"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "Opportunity not found. Please verify the opportunity exists."
            return f"API error: {e.response.status_code} - {e.response.text}"
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
