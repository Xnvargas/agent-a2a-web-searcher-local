"""
=============================================================================
SEARCH DOCUMENTS TOOL
=============================================================================

Semantic document search with automatic entity scoping.
When in an entity context, automatically filters to documents linked to that entity.

=============================================================================
"""

import os
import json
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class SearchDocumentsTool(LangChainTool):
    """
    Semantic document search with automatic entity filtering.

    Uses pgvector similarity search on the backend. Automatically applies
    scope filters (opportunityId, accountId) unless override_scope=True.
    """

    # -------------------------------------------------------------------------
    # Required class attributes
    # -------------------------------------------------------------------------
    name = "search_documents"
    description = (
        "Search documents semantically using natural language. "
        "Automatically filters to the current context (opportunity/account) "
        "unless override_scope is True. Returns relevant document chunks with "
        "content and metadata. Use this to find relevant documentation, past "
        "proposals, technical specs, or any uploaded content."
    )

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------
    api_base_url: str = os.getenv("SWOT_API_BASE", "http://localhost:3000")
    timeout: float = 30.0

    # -------------------------------------------------------------------------
    # Required: Parameter schema
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Required: Execute implementation
    # -------------------------------------------------------------------------
    async def execute(
        self,
        query: str,
        limit: int = 5,
        override_scope: bool = False
    ) -> str:
        """
        Execute semantic document search.

        Args:
            query: Natural language search query
            limit: Max results (default 5)
            override_scope: If True, ignore current context filters

        Returns:
            Formatted string with search results or error message
        """
        try:
            # Validate limit
            limit = max(1, min(20, limit))

            # Build request payload
            payload: Dict[str, Any] = {
                "query": query,
                "limit": limit
            }

            # Apply automatic scope filtering unless overridden
            scope_applied = False
            if not override_scope:
                filters = SWOTContext.get_filters()
                if filters:
                    payload.update(filters)
                    scope_applied = True

            # Call SWOT backend API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/documents/search",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            results = data.get('results', [])

            # Handle no results
            if not results:
                scope = SWOTContext.get_scope()
                if scope_applied and scope:
                    return (
                        f"No documents found matching '{query}' within the current "
                        f"{scope.type} scope. Try with override_scope=True to search "
                        f"all documents."
                    )
                return f"No documents found matching '{query}'."

            # Format results for LLM consumption
            formatted_results = []
            for i, r in enumerate(results, 1):
                title = r.get('document_title', 'Untitled')
                similarity = r.get('similarity', 0)
                content = r.get('chunk_content', '')[:400]
                page = r.get('page_number')

                result_str = f"{i}. **{title}** (relevance: {similarity:.0%})"
                if page:
                    result_str += f" [Page {page}]"
                result_str += f"\n   {content}"
                if len(r.get('chunk_content', '')) > 400:
                    result_str += "..."

                formatted_results.append(result_str)

            # Build response header
            scope_msg = ""
            if scope_applied:
                scope = SWOTContext.get_scope()
                if scope:
                    scope_msg = f" (filtered to current {scope.type})"

            return (
                f"Found {len(results)} relevant documents{scope_msg}:\n\n" +
                "\n\n".join(formatted_results)
            )

        except httpx.HTTPStatusError as e:
            return f"Search API error: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Search request failed: {str(e)}"
        except Exception as e:
            return f"Error searching documents: {str(e)}"

    # -------------------------------------------------------------------------
    # Required: LangChain tool function (for LLM binding)
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Optional: Citation metadata for source tracking
    # -------------------------------------------------------------------------
    def get_citation_metadata(self, tool_args: Dict, tool_result: str) -> Dict:
        ctx = SWOTContext.get_current()
        return {
            "tool": self.name,
            "query": tool_args.get("query", ""),
            "scope_type": ctx.scope.type if ctx else "global",
            "source_type": "document_search"
        }
