"""
=============================================================================
FIND SIMILAR SOLUTIONS TOOL
=============================================================================

Find past solutions similar to a use case description.
Migrated from httpx HTTP proxy to direct DB access:
- AgentEmbedder (ollama SDK) for query vector generation
- SQLDatabase for calling find_similar_solutions() PostgreSQL function

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.vector_search import find_similar_solutions as db_similar


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
        """Find similar solutions based on use case via direct DB access."""
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

            # Direct DB call: AgentEmbedder → find_similar_solutions() SQL function
            exclude_opp = ctx.scope.opportunity_id if ctx else None

            result = await db_similar(
                use_case_text=search_text,
                limit=limit,
                exclude_opportunity_id=exclude_opp,
            )

            if not result or result.strip() == '' or result.strip() == '[]':
                return "No similar solutions found. This might be a novel use case."

            header = "Similar solutions found"
            if ctx and ctx.scope.opportunity_id:
                header += " (excluding current opportunity)"

            return header + ":\n\n" + result

        except Exception as e:
            return f"Error finding similar solutions: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def find_similar_solutions(use_case: Optional[str] = None, limit: int = 5) -> str:
            """Find solutions similar to a use case. Uses current opportunity's use case if not provided."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return find_similar_solutions
