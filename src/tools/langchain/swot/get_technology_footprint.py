"""
=============================================================================
GET TECHNOLOGY FOOTPRINT TOOL
=============================================================================

Get IBM technology products deployed at an account.
Uses current context's account if not specified.

=============================================================================
"""

import os
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class GetTechnologyFootprintTool(LangChainTool):
    """
    Get IBM technology deployed at an account.

    Useful for understanding existing installations before proposing solutions.
    """

    name = "get_technology_footprint"
    description = (
        "Get IBM technology products deployed at an account. "
        "If no account_id provided, uses the current context's account. "
        "Returns list of products with categories. Use this to understand "
        "what IBM technology a client already has before proposing solutions."
    )

    api_base_url: str = os.getenv("SWOT_API_BASE", "http://localhost:3000")
    timeout: float = 30.0

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "account_id": {
                "type": "string",
                "required": False,
                "description": "Account UUID. If not provided, uses current context's account."
            }
        }

    async def execute(self, account_id: Optional[str] = None) -> str:
        """Get technology footprint for an account."""
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
                    f"{self.api_base_url}/api/accounts/{target_account}/footprint"
                )
                response.raise_for_status()
                data = response.json()

            products = data.get('products', [])
            account_name = data.get('account_name', 'Unknown')

            if not products:
                return f"No IBM technology products found deployed at {account_name}."

            # Group by category
            by_category: Dict[str, list] = {}
            for p in products:
                cat = p.get('category', 'Other')
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(p.get('name', 'Unknown'))

            # Format output
            lines = [f"IBM Technology at **{account_name}**:\n"]
            for category, prods in sorted(by_category.items()):
                lines.append(f"**{category}:**")
                for prod in prods:
                    lines.append(f"  - {prod}")

            lines.append(f"\nTotal: {len(products)} products")

            return '\n'.join(lines)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "Account not found."
            return f"API error: {e.response.status_code}"
        except Exception as e:
            return f"Error fetching technology footprint: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def get_technology_footprint(account_id: Optional[str] = None) -> str:
            """Get IBM technology products deployed at an account."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_technology_footprint
