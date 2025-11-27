"""
=============================================================================
FIRECRAWL SEARCH TOOL - Search the Web with Content Extraction
=============================================================================

This tool combines web search with optional content extraction. It searches
the web and can optionally scrape the content from search results.

WHEN TO USE:
- You need to search the web for information
- You want search results with actual page content extracted
- You need search + scrape in one operation

USE SEARX_SEARCH INSTEAD WHEN:
- You just need search results (URLs, titles, snippets)
- You want results from multiple search engines
- You don't need the full page content

=============================================================================
"""

from typing import Any, Dict
from datetime import datetime
from langchain_core.tools import tool

from tools.mcp.base import MCPTool
from . import FIRECRAWL_MCP_URL


class FirecrawlSearchTool(MCPTool):
    """
    Tool for searching the web and extracting content using Firecrawl MCP.
    
    This tool performs a web search and can optionally extract the full
    content from each search result. Useful when you need both discovery
    and content in one operation.
    
    Features:
        - Web search functionality
        - Optional content extraction from results
        - Language and country filtering
        - Configurable result limit
    
    Example Usage:
        ```python
        tool = FirecrawlSearchTool()
        result = await tool.execute(
            query="python machine learning tutorial",
            limit=5,
            lang="en"
        )
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_search"
    description = "Search the web and optionally extract content from search results."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the search tool."""
        return {
            "query": {
                "type": "string",
                "required": True,
                "description": "The search query string."
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 5,
                "description": "Number of results to return. Default: 5"
            },
            "lang": {
                "type": "string",
                "required": False,
                "default": "en",
                "description": "Language code for results (e.g., 'en', 'es', 'fr'). Default: 'en'"
            },
            "country": {
                "type": "string",
                "required": False,
                "default": "us",
                "description": "Country code for results (e.g., 'us', 'uk', 'de'). Default: 'us'"
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_search(
            query: str,
            limit: int = 5,
            lang: str = "en",
            country: str = "us"
        ) -> str:
            """
            Search the web and optionally extract content from search results.
            
            Use this tool when you need to search for information and get the
            actual content from the results. For simple searches without content
            extraction, use searx_search instead.
            
            Args:
                query: Search query string
                limit: Number of results to return (default: 5)
                lang: Language code (default: 'en')
                country: Country code (default: 'us')
            
            Returns:
                Search results with optional extracted content
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_search
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from search results."""
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "web_search",
            "search_query": tool_args.get("query", ""),
            "result_limit": tool_args.get("limit", 5),
            "language": tool_args.get("lang", "en"),
            "country": tool_args.get("country", "us"),
        }
