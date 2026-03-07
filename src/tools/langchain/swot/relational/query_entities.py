"""
=============================================================================
QUERY ENTITIES TOOL (NEW)
=============================================================================

Search for accounts, opportunities, or products by name, status, or filters.
Enables the agent to find entities when operating without page context,
or to explore data beyond the current scope.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query


class QueryEntitiesTool(LangChainTool):
    """
    Search for entities (accounts, opportunities, products) via SQLDatabase.

    Useful for finding entities when operating without page context,
    or to explore data beyond the current scope.
    """

    name = "query_entities"
    description = (
        "Search for accounts, opportunities, products, or solutions by name, "
        "status, or filters. Use this to find entities when operating without "
        "page context, or to explore data beyond the current scope."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "entity_type": {
                "type": "string",
                "required": True,
                "description": "Type of entity to search: 'account', 'opportunity', 'product', or 'solution'"
            },
            "search_term": {
                "type": "string",
                "required": False,
                "description": "Name or partial name to search for (case-insensitive)"
            },
            "status": {
                "type": "string",
                "required": False,
                "description": "Filter by status (applies to opportunities)"
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 10,
                "description": "Maximum results to return (1-20, default: 10)"
            }
        }

    async def execute(
        self,
        entity_type: str,
        search_term: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """Query entities via direct SQLDatabase queries."""
        try:
            limit = max(1, min(20, limit))

            if entity_type == "account":
                where = "WHERE 1=1"
                if search_term:
                    safe = search_term.replace("'", "''")
                    where += f" AND name ILIKE '%{safe}%'"

                result = run_query(f"""
                    SELECT id, name, industry, segment, pod
                    FROM accounts {where}
                    ORDER BY name LIMIT {limit}
                """)

            elif entity_type == "opportunity":
                where = "WHERE 1=1"
                if search_term:
                    safe = search_term.replace("'", "''")
                    where += f" AND o.name ILIKE '%{safe}%'"
                if status:
                    safe_status = status.replace("'", "''")
                    where += f" AND o.status = '{safe_status}'"

                result = run_query(f"""
                    SELECT o.id, o.name, o.status, o.value, a.name as account_name
                    FROM opportunities o
                    JOIN accounts a ON a.id = o.account_id
                    {where}
                    ORDER BY o.updated_at DESC LIMIT {limit}
                """)

            elif entity_type == "product":
                where = "WHERE 1=1"
                if search_term:
                    safe = search_term.replace("'", "''")
                    where += f" AND name ILIKE '%{safe}%'"

                result = run_query(f"""
                    SELECT id, name, category, vendor, ownership
                    FROM products {where}
                    ORDER BY name LIMIT {limit}
                """)

            elif entity_type == "solution":
                conditions = ["1=1"]
                if search_term:
                    safe_term = search_term.replace("'", "''")
                    conditions.append(
                        f"(s.overview ILIKE '%{safe_term}%' OR o.name ILIKE '%{safe_term}%')"
                    )
                if status:
                    safe_status = status.replace("'", "''")
                    conditions.append(f"s.status = '{safe_status}'")

                where_clause = " AND ".join(conditions)
                result = run_query(f"""
                    SELECT s.id, s.status, s.version,
                        o.name as opportunity_name, a.name as account_name,
                        LEFT(s.overview, 200) as overview_preview
                    FROM solutions s
                    JOIN opportunities o ON o.id = s.opportunity_id
                    JOIN accounts a ON a.id = o.account_id
                    WHERE {where_clause}
                    ORDER BY s.updated_at DESC
                    LIMIT {limit}
                """)
                return f"Solutions found:\n{result}" if result and result.strip() and result.strip() != '[]' else "No solutions found."

            else:
                return f"Unknown entity_type: {entity_type}. Use 'account', 'opportunity', 'product', or 'solution'."

            if not result or result.strip() == '' or result.strip() == '[]':
                return f"No {entity_type} records found matching your criteria."

            return result

        except Exception as e:
            return f"Error querying entities: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def query_entities(
            entity_type: str,
            search_term: Optional[str] = None,
            status: Optional[str] = None,
            limit: int = 10
        ) -> str:
            """Search for accounts, opportunities, products, or solutions by name, status, or filters."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return query_entities
