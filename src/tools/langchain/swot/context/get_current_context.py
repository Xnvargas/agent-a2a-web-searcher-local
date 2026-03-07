"""
=============================================================================
GET CURRENT CONTEXT TOOL
=============================================================================

Returns information about the current page context.
Useful when user asks "what opportunity is this?" or "tell me about this account".

=============================================================================
"""

import json
from typing import Dict, Any
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class GetCurrentContextTool(LangChainTool):
    """
    Get details about the current context the agent is operating in.

    This tool doesn't call any external API - it reads from the context
    that was passed when the user opened the AI assistant.
    """

    name = "get_current_context"
    description = (
        "Get details about the current context. "
        "NOTE: In opportunity, account, and product views, the context is already "
        "provided in your system prompt including all entity IDs. You do NOT need "
        "to call this tool to get opportunity_id, solution_id, etc. — they are "
        "already available to you. "
        "Use this tool ONLY when: (1) you are in global/dashboard mode and need "
        "to check if context exists, or (2) you suspect the context may have "
        "changed since the conversation started."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        # No parameters - reads from context
        return {}

    async def execute(self) -> str:
        """Get current context information."""
        ctx = SWOTContext.get_current()

        if not ctx:
            return json.dumps({
                "mode": "global",
                "message": "No specific context. Operating in global mode with access to all data.",
                "available_actions": [
                    "Search all documents",
                    "Find similar solutions",
                    "Query any account's technology footprint"
                ]
            }, indent=2)

        scope = ctx.scope
        summary = ctx.summary

        # Build response based on scope type
        result: Dict[str, Any] = {
            "mode": scope.type,
            "entity_name": summary.entity_name,
        }

        if scope.type == 'opportunity':
            result.update({
                "opportunity_id": scope.opportunity_id,
                "account": {
                    "name": summary.account_name,
                    "industry": summary.industry,
                    "id": scope.account_id
                },
                "use_case": summary.use_case,
                "strategy": summary.strategy,
                "success_criteria": summary.success_criteria,
                "status": summary.status,
                "classification": summary.classification,
                "products": [
                    {"name": p.get('name'), "is_primary": p.get('isPrimary')}
                    for p in (summary.products or [])
                ],
                "contacts": [
                    {"name": c.get('name'), "title": c.get('title'), "influence": c.get('influenceLevel')}
                    for c in (summary.contacts or [])[:5]
                ],
                "solution": {
                    "id": scope.solution_id,
                    "status": summary.solution_status,
                    "version": summary.solution_version if hasattr(summary, 'solution_version') else None,
                    "has_draft": bool(summary.solution_overview),
                    "overview_preview": (summary.solution_overview or "")[:200] if summary.solution_overview else None
                }
            })

        elif scope.type == 'account':
            result.update({
                "account_id": scope.account_id,
                "industry": summary.industry,
                "segment": summary.segment,
                "technology_footprint": [
                    {"name": t.get('name'), "category": t.get('category')}
                    for t in (summary.technology_footprint or [])
                ],
                "team_members": [
                    {"name": tm.get('name'), "role": tm.get('role')}
                    for tm in (summary.team_members or [])[:5]
                ]
            })

        elif scope.type == 'solution':
            result.update({
                "solution_id": scope.solution_id,
                "parent_opportunity": {
                    "id": scope.opportunity_id,
                    "name": summary.entity_name
                },
                "account": summary.account_name,
                "solution_status": summary.solution_status,
                "has_overview": bool(summary.solution_overview),
                "overview_preview": (summary.solution_overview or "")[:300] + "..." if summary.solution_overview and len(summary.solution_overview) > 300 else summary.solution_overview
            })

        elif scope.type == 'product':
            result.update({
                "product_id": scope.product_id,
                "vendor": summary.vendor,
                "category": summary.category,
                "ownership": summary.ownership,
                "description": summary.product_description,
                "documentation_url": summary.documentation_url,
                "document_count": summary.document_count,
                "linked_accounts": [
                    {"name": a.get('name'), "industry": a.get('industry')}
                    for a in (summary.linked_accounts or [])
                ],
                "linked_opportunities": [
                    {"name": o.get('name'), "status": o.get('status'), "account": o.get('accountName')}
                    for o in (summary.linked_opportunities or [])
                ],
                "available_actions": [
                    "Search this product's documents",
                    "View linked accounts",
                    "View linked opportunities",
                    "Get product details"
                ]
            })

        elif scope.type == 'product-list':
            result.update({
                "message": "Viewing all products. Can search documentation across all products.",
                "available_actions": [
                    "Search all product documents",
                    "Find products by name or category",
                    "Compare products",
                    "Get details for any product"
                ]
            })

        elif scope.type == 'dashboard':
            result.update({
                "message": "Viewing dashboard - pipeline overview",
                "available_actions": [
                    "Search all documents",
                    "Find opportunities",
                    "Query accounts"
                ]
            })

        return json.dumps(result, indent=2)

    def get_langchain_tool(self):
        @tool
        def get_current_context() -> str:
            """Get details about the current context (opportunity, account, or global view)."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_current_context
