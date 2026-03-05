"""
=============================================================================
GET ENTITY DETAILS TOOL (NEW)
=============================================================================

Retrieve detailed information about a specific entity by ID.
Supports accounts, opportunities, products, contacts, and solutions.

=============================================================================
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query


class GetEntityDetailsTool(LangChainTool):
    """
    Get detailed information about a specific entity via SQLDatabase.

    Retrieves full details including related data for a given entity ID.
    """

    name = "get_entity_details"
    description = (
        "Get detailed information about a specific entity by its ID. "
        "Supports entity types: 'account', 'opportunity', 'product', "
        "'contact', 'solution', 'document'. "
        "Returns full details including related data."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "entity_type": {
                "type": "string",
                "required": True,
                "description": "Type of entity: 'account', 'opportunity', 'product', 'contact', 'solution', or 'document'"
            },
            "entity_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the entity to retrieve"
            }
        }

    async def execute(self, entity_type: str, entity_id: str) -> str:
        """Get entity details via direct SQLDatabase queries."""
        try:
            safe_id = entity_id.replace("'", "''")

            if entity_type == "account":
                result = run_query(f"""
                    SELECT a.id, a.name, a.industry, a.segment, a.pod,
                        a.created_at, a.updated_at
                    FROM accounts a
                    WHERE a.id = '{safe_id}'::uuid
                """)

                if not result or result.strip() == '' or result.strip() == '[]':
                    return f"Account not found with ID: {entity_id}"

                # Also get related opportunities
                opps = run_query(f"""
                    SELECT o.id, o.name, o.status, o.value
                    FROM opportunities o
                    WHERE o.account_id = '{safe_id}'::uuid
                    ORDER BY o.updated_at DESC LIMIT 10
                """)

                return f"Account details:\n{result}\n\nRelated opportunities:\n{opps}"

            elif entity_type == "opportunity":
                result = run_query(f"""
                    SELECT o.id, o.name, o.status, o.value, o.use_case,
                        o.strategy, o.success_criteria, o.classification,
                        a.name as account_name, a.industry
                    FROM opportunities o
                    JOIN accounts a ON a.id = o.account_id
                    WHERE o.id = '{safe_id}'::uuid
                """)

                if not result or result.strip() == '' or result.strip() == '[]':
                    return f"Opportunity not found with ID: {entity_id}"

                # Get products for this opportunity
                products = run_query(f"""
                    SELECT p.name, p.category, op.is_primary
                    FROM opportunity_products op
                    JOIN products p ON p.id = op.product_id
                    WHERE op.opportunity_id = '{safe_id}'::uuid
                """)

                return f"Opportunity details:\n{result}\n\nProducts:\n{products}"

            elif entity_type == "product":
                result = run_query(f"""
                    SELECT id, name, category, vendor, ownership
                    FROM products
                    WHERE id = '{safe_id}'::uuid
                """)

                if not result or result.strip() == '' or result.strip() == '[]':
                    return f"Product not found with ID: {entity_id}"

                return f"Product details:\n{result}"

            elif entity_type == "contact":
                result = run_query(f"""
                    SELECT c.id, c.name, c.title, c.email, c.influence_level
                    FROM contacts c
                    WHERE c.id = '{safe_id}'::uuid
                """)

                if not result or result.strip() == '' or result.strip() == '[]':
                    return f"Contact not found with ID: {entity_id}"

                return f"Contact details:\n{result}"

            elif entity_type == "solution":
                result = run_query(f"""
                    SELECT s.id, s.overview, s.architecture_details, s.implementation_notes,
                        s.status, s.version,
                        o.name as opportunity_name, a.name as account_name
                    FROM solutions s
                    JOIN opportunities o ON o.id = s.opportunity_id
                    JOIN accounts a ON a.id = o.account_id
                    WHERE s.id = '{safe_id}'::uuid
                """)

                if not result or result.strip() == '' or result.strip() == '[]':
                    return f"Solution not found with ID: {entity_id}"

                return f"Solution details:\n{result}"

            elif entity_type == "document":
                result = run_query(f"""
                    SELECT d.id, d.title, d.filename, d.category, d.status,
                        d.file_size_bytes, d.page_count,
                        COALESCE(LENGTH(d.extracted_text), 0) as text_length
                    FROM ag_catalog.documents d
                    WHERE d.id = '{safe_id}'::uuid
                """)

                if not result or result.strip() == '' or result.strip() == '[]':
                    return f"Document not found with ID: {entity_id}"

                return f"Document details:\n{result}"

            else:
                return (
                    f"Unknown entity_type: {entity_type}. "
                    "Use 'account', 'opportunity', 'product', 'contact', 'solution', or 'document'."
                )

        except Exception as e:
            return f"Error getting entity details: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def get_entity_details(entity_type: str, entity_id: str) -> str:
            """Get detailed information about a specific entity by its ID."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_entity_details
