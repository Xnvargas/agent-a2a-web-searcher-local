"""
=============================================================================
FIRECRAWL SCRAPE TOOL - Scrape Content from a Single URL
=============================================================================

This tool scrapes content from a single URL and returns it in the specified
format (markdown, HTML, etc.). It's the primary tool for extracting content
from individual web pages.

WHEN TO USE:
- You have a specific URL you want to scrape
- You need the content of a single page
- You want clean markdown/HTML output

USE FIRECRAWL_CRAWL INSTEAD WHEN:
- You need to scrape multiple pages from a site
- You want to follow links and scrape recursively

=============================================================================
"""

import os
from typing import Any, Dict, List
from datetime import datetime
from langchain_core.tools import tool

from tools.mcp.base import MCPTool
from . import FIRECRAWL_MCP_URL


class FirecrawlScrapeTool(MCPTool):
    """
    Tool for scraping content from a single URL using Firecrawl MCP.
    
    This is the most commonly used Firecrawl tool. It fetches a URL and
    returns the content in a clean, structured format (typically markdown).
    
    Features:
        - Returns content as markdown, HTML, or other formats
        - Can extract only main content (removes navigation, ads, etc.)
        - Handles JavaScript-rendered pages (via waitFor parameter)
        - Configurable timeout for slow pages
    
    Example Usage:
        ```python
        tool = FirecrawlScrapeTool()
        result = await tool.execute(
            url="https://example.com/article",
            formats=["markdown"],
            onlyMainContent=True
        )
        ```
    
    Citation:
        This tool extracts citation metadata including the actual scraped URL
        (which may differ from input due to redirects), content format, and
        a preview of the scraped content.
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_scrape"
    """Tool name - must match the function name in get_langchain_tool()."""
    
    description = "Scrape content from a single URL with advanced options. Returns markdown or HTML content."
    """Description shown to the LLM when selecting tools."""
    
    mcp_server_url = FIRECRAWL_MCP_URL
    """URL of the Firecrawl MCP server."""
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Define the parameters for the scrape tool.
        
        Returns:
            Parameter schema with URL (required) and optional scraping settings.
        """
        return {
            "url": {
                "type": "string",
                "required": True,
                "description": "The URL to scrape. Must be a valid HTTP/HTTPS URL."
            },
            "formats": {
                "type": "array",
                "required": False,
                "default": ["markdown"],
                "description": "Output formats. Options: 'markdown', 'html', 'rawHtml', 'screenshot'. Default: ['markdown']"
            },
            "onlyMainContent": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "If true, extracts only the main content (removes nav, footer, ads). Default: true"
            },
            "waitFor": {
                "type": "integer",
                "required": False,
                "default": 0,
                "description": "Milliseconds to wait before scraping (for JS-rendered content). Default: 0"
            },
            "timeout": {
                "type": "integer",
                "required": False,
                "default": 30000,
                "description": "Request timeout in milliseconds. Default: 30000 (30 seconds)"
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """
        Return the LangChain @tool decorated function.
        
        The function signature matches the schema parameters.
        The docstring becomes the tool description in LangChain.
        """
        @tool
        def firecrawl_scrape(
            url: str, 
            formats: List[str] = None, 
            onlyMainContent: bool = True, 
            waitFor: int = 0, 
            timeout: int = 30000
        ) -> str:
            """
            Scrape content from a single URL with advanced options.
            
            Use this tool to extract content from a web page. The content is
            returned in a clean format (markdown by default), with navigation
            and other non-content elements removed.
            
            Args:
                url: The URL to scrape
                formats: Output formats (default: ['markdown'])
                onlyMainContent: Extract only main content (default: True)
                waitFor: Wait time in ms for JS content (default: 0)
                timeout: Timeout in milliseconds (default: 30000)
            
            Returns:
                Scraped content as markdown/HTML string
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_scrape
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """
        Extract citation metadata from scrape results.
        
        Attempts to extract the actual scraped URL from the result metadata,
        which may differ from the input URL due to redirects.
        """
        citation = {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "web_scrape",
            "url": tool_args.get("url", ""),
            "content_format": tool_args.get("formats", ["markdown"])[0] if tool_args.get("formats") else "markdown",
            "main_content_only": tool_args.get("onlyMainContent", True),
        }
        
        # Try to extract actual URL from result (handles redirects)
        if isinstance(tool_result, dict):
            if "metadata" in tool_result and "sourceURL" in tool_result["metadata"]:
                citation["url"] = tool_result["metadata"]["sourceURL"]
        
        # Add content preview
        if isinstance(tool_result, str):
            preview = tool_result[:200]
            if len(tool_result) > 200:
                preview += "..."
            citation["content_preview"] = preview
        
        return citation
