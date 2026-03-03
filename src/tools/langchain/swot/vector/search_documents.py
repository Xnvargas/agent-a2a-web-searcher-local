"""
=============================================================================
SEARCH DOCUMENTS TOOL
=============================================================================

Semantic document search with automatic entity scoping.
Migrated from httpx HTTP proxy to direct DB access:
- AgentEmbedder (ollama SDK) for query vector generation
- SQLDatabase for calling search_documents() PostgreSQL function

=============================================================================
"""

import asyncio
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.vector_search import search_documents as db_search
from utils.db.vector_search import search_documents_fulltext as db_fulltext_search


class SearchDocumentsTool(LangChainTool):
    """
    Semantic document search with automatic entity filtering.

    Uses AgentEmbedder + pgvector search_documents() SQL function directly.
    Automatically applies scope filters (opportunityId, accountId) unless
    override_scope=True.
    """

    name = "search_documents"
    description = (
        "Search documents semantically using natural language. "
        "Automatically filters to the current context (opportunity/account) "
        "unless override_scope is True. Returns relevant document chunks with "
        "content and metadata. Use this to find relevant documentation, past "
        "proposals, technical specs, or any uploaded content."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "query": {
                "type": "string",
                "required": True,
                "description": "Natural language search query describing what you're looking for"
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 5,
                "description": "Maximum number of results to return (1-20, default: 5)"
            },
            "override_scope": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "If True, search ALL documents regardless of current context. Use when user explicitly asks to search outside current scope."
            }
        }

    async def execute(
        self,
        query: str,
        limit: int = 5,
        override_scope: bool = False
    ) -> str:
        """Execute semantic and fulltext document search via direct DB access."""
        try:
            limit = max(1, min(20, limit))

            # Determine scope filters
            filters = {}
            scope_applied = False
            if not override_scope:
                filters = SWOTContext.get_filters()
                if filters:
                    scope_applied = True

            # Run both searches concurrently
            semantic_results, fulltext_results = await asyncio.gather(
                db_search(
                    query_text=query,
                    account_id=filters.get('accountId'),
                    opportunity_id=filters.get('opportunityId'),
                    solution_id=filters.get('solutionId'),
                    product_ids=filters.get('productIds'),
                    limit=limit,
                ),
                db_fulltext_search(
                    query_text=query,
                    account_id=filters.get('accountId'),
                    opportunity_id=filters.get('opportunityId'),
                    solution_id=filters.get('solutionId'),
                    product_ids=filters.get('productIds'),
                    limit=limit,
                ),
            )

            # Combine results
            combined = []
            if semantic_results and semantic_results.strip() and semantic_results.strip() != '[]':
                combined.append(f"**Semantic results (chunk-level):**\n{semantic_results}")
            if fulltext_results and fulltext_results.strip() and fulltext_results.strip() != '[]':
                combined.append(f"**Fulltext results (document-level):**\n{fulltext_results}")

            if not combined:
                scope = SWOTContext.get_scope()
                if scope_applied and scope:
                    return (
                        f"No documents found matching '{query}' within the current "
                        f"{scope.type} scope. Try with override_scope=True to search "
                        f"all documents."
                    )
                return f"No documents found matching '{query}'."

            # Build response header with scope info
            scope_msg = ""
            if scope_applied:
                scope = SWOTContext.get_scope()
                if scope:
                    scope_msg = f" (filtered to current {scope.type})"

            return f"Document search results{scope_msg}:\n\n" + "\n\n".join(combined)

        except Exception as e:
            return f"Error searching documents: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def search_documents(
            query: str,
            limit: int = 5,
            override_scope: bool = False
        ) -> str:
            """Search documents semantically. Automatically filters to current context unless override_scope=True."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return search_documents

    def get_citation_metadata(self, tool_args: Dict, tool_result: str) -> Dict:
        ctx = SWOTContext.get_current()
        return {
            "tool": self.name,
            "query": tool_args.get("query", ""),
            "scope_type": ctx.scope.type if ctx else "global",
            "source_type": "document_search"
        }
