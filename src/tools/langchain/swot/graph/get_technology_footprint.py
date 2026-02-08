"""
=============================================================================
GET TECHNOLOGY FOOTPRINT TOOL
=============================================================================

Get IBM technology products deployed at an account.
Migrated from httpx HTTP proxy to direct AGEGraph Cypher queries.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.graph import run_cypher


class GetTechnologyFootprintTool(LangChainTool):
    """
    Get IBM technology deployed at an account via AGEGraph.

    Useful for understanding existing installations before proposing solutions.
    AGEGraph handles LOAD 'age', search_path, Cypher→SQL, and agtype parsing.
    """

    name = "get_technology_footprint"
    description = (
        "Get IBM technology products deployed at an account. "
        "If no account_id provided, uses the current context's account. "
        "Returns list of products with categories. Use this to understand "
        "what IBM technology a client already has before proposing solutions."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "account_id": {
                "type": "string",
                "required": False,
                "description": "Account UUID. If not provided, uses current context's account."
            }
        }

    async def execute(self, account_id: Optional[str] = None) -> str:
        """Get technology footprint via direct AGEGraph Cypher query."""
        try:
            target = account_id or SWOTContext.get_account_id()
            if not target:
                return (
                    "No account_id provided and none available in current context. "
                    "Please specify an account_id or navigate to an account/opportunity page."
                )

            # Direct Cypher query via AGEGraph
            results = run_cypher(f"""
                MATCH (a:Account {{id: '{target}'}})-[:USES_TECHNOLOGY]->(p:Product)
                RETURN p.name AS name, p.category AS category, p.vendor AS vendor
            """)

            if not results:
                # Try to get account name from context
                ctx = SWOTContext.get_current()
                account_name = ctx.summary.account_name if ctx else "this account"
                return f"No IBM technology products found deployed at {account_name}."

            # Group by category
            by_category: Dict[str, list] = {}
            for r in results:
                cat = r.get('category', 'Other') or 'Other'
                if cat not in by_category:
                    by_category[cat] = []
                name = r.get('name', 'Unknown')
                vendor = r.get('vendor')
                entry = f"{name}" + (f" ({vendor})" if vendor else "")
                by_category[cat].append(entry)

            # Get account name from context
            ctx = SWOTContext.get_current()
            account_name = ctx.summary.account_name if ctx else target

            # Format output
            lines = [f"IBM Technology at **{account_name}**:\n"]
            for category, prods in sorted(by_category.items()):
                lines.append(f"**{category}:**")
                for prod in prods:
                    lines.append(f"  - {prod}")

            lines.append(f"\nTotal: {len(results)} products")

            return '\n'.join(lines)

        except Exception as e:
            return f"Error fetching technology footprint: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def get_technology_footprint(account_id: Optional[str] = None) -> str:
            """Get IBM technology products deployed at an account."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_technology_footprint
