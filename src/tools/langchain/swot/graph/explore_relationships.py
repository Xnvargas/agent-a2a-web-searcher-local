"""
=============================================================================
EXPLORE RELATIONSHIPS TOOL (NEW)
=============================================================================

Flexible graph exploration using AGEGraph Cypher queries.
Supports multiple query types for navigating the knowledge graph.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.graph import run_cypher


class ExploreRelationshipsTool(LangChainTool):
    """
    Explore relationships in the knowledge graph via AGEGraph.

    Supports multiple query types for navigating entity relationships.
    """

    name = "explore_relationships"
    description = (
        "Explore relationships in the knowledge graph. Find: "
        "team members covering an account (query_type='account_team'), "
        "opportunities involving a product (query_type='product_opportunities'), "
        "a team member's product expertise (query_type='member_expertise'), "
        "or all accounts a team member covers (query_type='member_accounts')."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "query_type": {
                "type": "string",
                "required": True,
                "description": (
                    "Type of relationship query: 'account_team', 'product_opportunities', "
                    "'member_expertise', or 'member_accounts'"
                )
            },
            "entity_id": {
                "type": "string",
                "required": False,
                "description": "UUID of the entity to query (account, team member)"
            },
            "entity_name": {
                "type": "string",
                "required": False,
                "description": "Name of the entity to query (used for product lookups)"
            }
        }

    async def execute(
        self,
        query_type: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None
    ) -> str:
        """Explore relationships via direct AGEGraph Cypher queries."""
        try:
            if query_type == "account_team":
                if not entity_id:
                    return "entity_id required for account_team query."
                results = run_cypher(f"""
                    MATCH (tm:TeamMember)-[r:COVERS]->(a:Account {{id: '{entity_id}'}})
                    RETURN tm.name AS name, tm.role AS role, r.role AS account_role, r.is_primary AS is_primary
                """)

            elif query_type == "product_opportunities":
                if not entity_name:
                    return "entity_name required for product_opportunities query."
                safe = entity_name.replace("'", "\\'")
                results = run_cypher(f"""
                    MATCH (o:Opportunity)-[:INVOLVES_PRODUCT]->(p:Product {{name: '{safe}'}})
                    RETURN o.id AS id, o.name AS name, o.status AS status
                """)

            elif query_type == "member_expertise":
                if not entity_id:
                    return "entity_id required for member_expertise query."
                results = run_cypher(f"""
                    MATCH (tm:TeamMember {{id: '{entity_id}'}})-[:HAS_EXPERTISE]->(p:Product)
                    RETURN p.name AS name, p.category AS category, p.vendor AS vendor
                """)

            elif query_type == "member_accounts":
                if not entity_id:
                    return "entity_id required for member_accounts query."
                results = run_cypher(f"""
                    MATCH (tm:TeamMember {{id: '{entity_id}'}})-[r:COVERS]->(a:Account)
                    RETURN a.name AS name, a.industry AS industry, r.role AS role
                """)

            else:
                return (
                    "Unknown query_type. Options: account_team, product_opportunities, "
                    "member_expertise, member_accounts"
                )

            if not results:
                return f"No results found for {query_type} query."

            # Format results for LLM consumption
            formatted = []
            for r in results:
                parts = []
                for key, value in r.items():
                    if value is not None:
                        parts.append(f"{key}: {value}")
                formatted.append("- " + ", ".join(parts))

            return f"Found {len(results)} results:\n" + "\n".join(formatted)

        except Exception as e:
            return f"Error exploring relationships: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def explore_relationships(
            query_type: str,
            entity_id: Optional[str] = None,
            entity_name: Optional[str] = None
        ) -> str:
            """Explore relationships in the knowledge graph."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return explore_relationships
