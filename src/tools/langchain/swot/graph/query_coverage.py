"""
=============================================================================
QUERY COVERAGE TOOL
=============================================================================

Find team members who cover a specific product for an account.
Migrated from httpx HTTP proxy to direct AGEGraph Cypher queries.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.graph import run_cypher


class QueryCoverageTool(LangChainTool):
    """
    Find who covers a specific product for an account via AGEGraph.

    Uses graph relationships to find team members with both:
    - Expertise in the product (HAS_EXPERTISE)
    - Coverage of the account (COVERS)
    """

    name = "query_coverage"
    description = (
        "Find team members who cover a specific product for an account. "
        "Searches for people with both product expertise AND account coverage. "
        "Account defaults to current context if not specified. "
        "Use this to find the right people to involve in an opportunity."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "product_name": {
                "type": "string",
                "required": True,
                "description": "Name of the product (e.g., 'watsonx.ai', 'Db2', 'Cloud Pak for Data')"
            },
            "account_id": {
                "type": "string",
                "required": False,
                "description": "Account UUID. If not provided, uses current context's account."
            }
        }

    async def execute(
        self,
        product_name: str,
        account_id: Optional[str] = None
    ) -> str:
        """Query coverage via direct AGEGraph Cypher query."""
        try:
            target = account_id or SWOTContext.get_account_id()
            if not target:
                return (
                    "No account_id provided and none available in current context. "
                    "Please specify an account_id or navigate to an account/opportunity page."
                )

            sanitized_name = product_name.replace("'", "\\'")

            # Direct Cypher query via AGEGraph
            results = run_cypher(f"""
                MATCH (tm:TeamMember)-[:HAS_EXPERTISE]->(p:Product)
                WHERE p.name = '{sanitized_name}'
                MATCH (tm)-[:COVERS]->(a:Account)
                WHERE a.id = '{target}'
                RETURN tm.id AS id, tm.name AS name, tm.role AS role, tm.email AS email
            """)

            if not results:
                return (
                    f"No team members found covering **{product_name}** for this account. "
                    f"This could mean:\n"
                    f"- No one has registered expertise in {product_name}\n"
                    f"- No one with {product_name} expertise covers this account\n"
                    f"Consider reaching out to the product team directly."
                )

            # Format results
            lines = [f"Team members covering **{product_name}** for this account:\n"]
            for r in results:
                name = r.get('name', 'Unknown')
                role = r.get('role', 'Unknown role')
                email = r.get('email')
                line = f"- **{name}** - {role}"
                if email:
                    line += f" ({email})"
                lines.append(line)

            return '\n'.join(lines)

        except Exception as e:
            return f"Error querying coverage: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def query_coverage(product_name: str, account_id: Optional[str] = None) -> str:
            """Find team members who cover a specific product for an account."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return query_coverage
