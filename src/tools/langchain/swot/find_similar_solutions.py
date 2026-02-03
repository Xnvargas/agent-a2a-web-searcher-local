"""
=============================================================================
FIND SIMILAR SOLUTIONS TOOL
=============================================================================

Find past solutions similar to a use case description.
Useful for finding reference architectures and patterns.

=============================================================================
"""

import os
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class FindSimilarSolutionsTool(LangChainTool):
    """
    Find solutions similar to a use case description.

    If no use_case is provided and we're in an opportunity context,
    automatically uses the current opportunity's use case.
    Excludes the current opportunity from results when in opportunity scope.
    """

    name = "find_similar_solutions"
    description = (
        "Find past solutions similar to a use case description. "
        "If no use_case provided and viewing an opportunity, automatically uses "
        "that opportunity's use case. Returns similar solutions with opportunity "
        "names, accounts, and similarity scores. Use this to find reference "
        "architectures and patterns from past work."
    )

    api_base_url: str = os.getenv("SWOT_API_BASE", "http://localhost:3000")
    timeout: float = 30.0

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "use_case": {
                "type": "string",
                "required": False,
                "description": (
                    "Use case description to match against. If not provided, "
                    "uses the current opportunity's use case from context."
                )
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 5,
                "description": "Maximum number of similar solutions to return (1-10)"
            }
        }

    async def execute(self, use_case: Optional[str] = None, limit: int = 5) -> str:
        """Find similar solutions based on use case."""
        try:
            limit = max(1, min(10, limit))

            # Get use case from context if not provided
            search_text = use_case
            ctx = SWOTContext.get_current()

            if not search_text:
                if ctx and ctx.summary.use_case:
                    search_text = ctx.summary.use_case
                else:
                    return (
                        "No use case provided and none available in current context. "
                        "Please provide a use case description to search for."
                    )

            # Build request
            payload: Dict[str, Any] = {
                "useCase": search_text,
                "limit": limit
            }

            # Exclude current opportunity from results
            if ctx and ctx.scope.opportunity_id:
                payload["excludeOpportunityId"] = ctx.scope.opportunity_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/solutions/similar",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            results = data.get('results', [])

            if not results:
                return "No similar solutions found. This might be a novel use case."

            # Format results
            formatted = []
            for i, r in enumerate(results, 1):
                opp_name = r.get('opportunity_name', 'Unknown')
                account = r.get('account_name', 'Unknown account')
                similarity = r.get('similarity', 0)
                use_case_preview = (r.get('use_case') or 'N/A')[:200]
                solution_preview = (r.get('solution_overview') or 'No solution details')[:150]

                formatted.append(
                    f"{i}. **{opp_name}** at {account} (similarity: {similarity:.0%})\n"
                    f"   Use case: {use_case_preview}{'...' if len(r.get('use_case', '')) > 200 else ''}\n"
                    f"   Solution: {solution_preview}{'...' if len(r.get('solution_overview', '')) > 150 else ''}"
                )

            header = f"Found {len(results)} similar solutions"
            if ctx and ctx.scope.opportunity_id:
                header += " (excluding current opportunity)"

            return header + ":\n\n" + "\n\n".join(formatted)

        except httpx.HTTPStatusError as e:
            return f"API error: {e.response.status_code}"
        except Exception as e:
            return f"Error finding similar solutions: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def find_similar_solutions(use_case: Optional[str] = None, limit: int = 5) -> str:
            """Find solutions similar to a use case. Uses current opportunity's use case if not provided."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return find_similar_solutions
