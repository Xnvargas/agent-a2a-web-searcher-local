"""
=============================================================================
FIRECRAWL MAP TOOL - Discover URLs on a Website
=============================================================================

This tool maps a website to discover all indexed URLs. Useful for finding
specific sections of a website before scraping.

WHEN TO USE:
- You want to discover what pages exist on a website
- You need to find specific sections/URLs before scraping
- You want to understand the structure of a site

=============================================================================
"""

from typing import Any, Dict
from datetime import datetime
from langchain_core.tools import tool

from tools.mcp.base import MCPTool
from . import FIRECRAWL_MCP_URL


class FirecrawlMapTool(MCPTool):
    """
    Tool for mapping/discovering URLs on a website using Firecrawl MCP.
    
    This tool crawls a website's sitemap and internal links to discover
    all available URLs. Useful for understanding site structure before
    scraping specific pages.
    
    Features:
        - Discovers all URLs on a website
        - Optional search filter to find specific URLs
        - Configurable limit on number of URLs returned
        - Can ignore query parameters for cleaner results
    
    Example Usage:
        ```python
        tool = FirecrawlMapTool()
        result = await tool.execute(
            url="https://example.com",
            search="blog",
            limit=50
        )
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_map"
    description = "Map a website to discover all indexed URLs. Best for finding specific sections of a website."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the map tool."""
        return {
            "url": {
                "type": "string",
                "required": True,
                "description": "The base URL of the website to map."
            },
            "search": {
                "type": "string",
                "required": False,
                "description": "Optional search term to filter URLs. Only URLs containing this term will be returned."
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 100,
                "description": "Maximum number of URLs to return. Default: 100"
            },
            "ignoreSitemap": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "If true, ignores the sitemap and only uses link discovery. Default: false"
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_map(
            url: str,
            search: str = None,
            limit: int = 100,
            ignoreSitemap: bool = False
        ) -> str:
            """
            Map a website to discover all indexed URLs.
            
            Use this tool when you need to discover what pages exist on a website
            before scraping specific ones. You can filter results by providing
            a search term.
            
            Args:
                url: The base URL of the website to map
                search: Optional search term to filter URLs
                limit: Maximum number of URLs to return (default: 100)
                ignoreSitemap: If true, only uses link discovery (default: false)
            
            Returns:
                JSON array of discovered URLs
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_map
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from map results."""
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "sitemap",
            "base_url": tool_args.get("url", ""),
            "search_filter": tool_args.get("search"),
            "url_limit": tool_args.get("limit", 100),
        }
