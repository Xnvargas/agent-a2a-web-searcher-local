"""
=============================================================================
FIRECRAWL BATCH TOOLS - Batch Scraping Multiple URLs
=============================================================================

These tools provide batch scraping capabilities for efficiently scraping
multiple URLs with built-in rate limiting.

WHEN TO USE:
- You have a list of specific URLs you want to scrape
- You want efficient batch processing with rate limiting
- You know exactly which pages you need (not crawling)

USE FIRECRAWL_CRAWL INSTEAD WHEN:
- You want to discover and crawl linked pages
- You don't know the exact URLs ahead of time

WORKFLOW:
1. Call firecrawl_batch_scrape with URL list (returns batch ID)
2. Call firecrawl_check_batch_status with the batch ID to check progress
3. Status will include results when complete

=============================================================================
"""

from typing import Any, Dict, List
from datetime import datetime
from langchain_core.tools import tool

from tools.mcp.base import MCPTool
from . import FIRECRAWL_MCP_URL


class FirecrawlBatchScrapeTool(MCPTool):
    """
    Tool for batch scraping multiple URLs using Firecrawl MCP.
    
    This tool efficiently scrapes multiple URLs with built-in rate limiting.
    Use this when you have a list of specific URLs to scrape rather than
    crawling/discovering pages.
    
    Features:
        - Batch processing of multiple URLs
        - Built-in rate limiting
        - Configurable scraping options
        - Asynchronous execution
    
    Example Usage:
        ```python
        tool = FirecrawlBatchScrapeTool()
        result = await tool.execute(
            urls=[
                "https://example.com/page1",
                "https://example.com/page2",
                "https://example.com/page3"
            ],
            options={"formats": ["markdown"], "onlyMainContent": True}
        )
        # result contains batch operation ID
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_batch_scrape"
    description = "Scrape multiple URLs efficiently with built-in rate limiting. Returns a batch ID for status checking."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the batch scrape tool."""
        return {
            "urls": {
                "type": "array",
                "required": True,
                "description": "Array of URLs to scrape."
            },
            "options": {
                "type": "object",
                "required": False,
                "description": "Optional scrape options for all URLs: formats, onlyMainContent, waitFor, timeout."
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_batch_scrape(
            urls: List[str],
            options: dict = None
        ) -> str:
            """
            Scrape multiple URLs efficiently with built-in rate limiting.
            
            Use this tool when you have a list of specific URLs to scrape.
            The batch operation runs asynchronously - use firecrawl_check_batch_status
            with the returned batch ID to check progress and get results.
            
            Args:
                urls: Array of URLs to scrape
                options: Optional scrape options (formats, onlyMainContent, etc.)
            
            Returns:
                Batch operation ID for status checking
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_batch_scrape
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from batch scrape job."""
        urls = tool_args.get("urls", [])
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "batch_scrape",
            "urls": urls[:5],  # First 5 URLs for citation
            "total_urls": len(urls),
        }


class FirecrawlCheckBatchStatusTool(MCPTool):
    """
    Tool for checking the status of a batch scraping operation.
    
    After starting a batch scrape with firecrawl_batch_scrape, use this
    tool to check if the operation is complete and get the results.
    
    Status Values:
        - "pending": Job is queued
        - "running": Scraping in progress
        - "completed": All URLs scraped (results included)
        - "failed": Operation failed (error message included)
    
    Example Usage:
        ```python
        tool = FirecrawlCheckBatchStatusTool()
        result = await tool.execute(id="batch_abc123")
        # Returns status and results if complete
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_check_batch_status"
    description = "Check the status of a batch scraping operation. Returns status and results when complete."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the check batch status tool."""
        return {
            "id": {
                "type": "string",
                "required": True,
                "description": "Batch operation ID returned from firecrawl_batch_scrape."
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_check_batch_status(id: str) -> str:
            """
            Check the status of a batch scraping operation.
            
            Use this tool after starting a batch scrape with firecrawl_batch_scrape
            to check if it's complete and get the results.
            
            Args:
                id: Batch operation ID returned from firecrawl_batch_scrape
            
            Returns:
                Status and results of the batch operation
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_check_batch_status
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from batch status check."""
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "batch_status",
            "batch_id": tool_args.get("id", ""),
        }
