"""
=============================================================================
QUERY COVERAGE TOOL
=============================================================================

Find team members who cover a specific product for an account.
Uses Apache AGE graph traversal in the backend.

=============================================================================
"""

import os
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class QueryCoverageTool(LangChainTool):
    """
    Find who covers a specific product for an account.

    Uses graph relationships to find team members with both:
    - Expertise in the product
    - Coverage of the account
    """

    name = "query_coverage"
    description = (
        "Find team members who cover a specific product for an account. "
        "Searches for people with both product expertise AND account coverage. "
        "Account defaults to current context if not specified. "
        "Use this to find the right people to involve in an opportunity."
    )

    api_base_url: str = os.getenv("SWOT_API_BASE", "http://localhost:3000")
    timeout: float = 30.0

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
        """Query coverage for a product at an account."""
        try:
            # Resolve account ID
            target_account = account_id
            if not target_account:
                target_account = SWOTContext.get_account_id()

            if not target_account:
                return (
                    "No account_id provided and none available in current context. "
                    "Please specify an account_id or navigate to an account/opportunity page."
                )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/coverage",
                    params={
                        "productName": product_name,
                        "accountId": target_account
                    }
                )
                response.raise_for_status()
                data = response.json()

            coverage = data.get('coverage', [])

            if not coverage:
                return (
                    f"No team members found covering **{product_name}** for this account. "
                    f"This could mean:\n"
                    f"- No one has registered expertise in {product_name}\n"
                    f"- No one with {product_name} expertise covers this account\n"
                    f"Consider reaching out to the product team directly."
                )

            # Format results
            lines = [f"Team members covering **{product_name}** for this account:\n"]
            for c in coverage:
                name = c.get('name', 'Unknown')
                role = c.get('role', 'Unknown role')
                lines.append(f"- **{name}** - {role}")

            return '\n'.join(lines)

        except httpx.HTTPStatusError as e:
            return f"API error: {e.response.status_code}"
        except Exception as e:
            return f"Error querying coverage: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def query_coverage(product_name: str, account_id: Optional[str] = None) -> str:
            """Find team members who cover a specific product for an account."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return query_coverage
