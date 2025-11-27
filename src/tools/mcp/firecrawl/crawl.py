"""
=============================================================================
FIRECRAWL CRAWL TOOLS - Asynchronous Website Crawling
=============================================================================

These tools provide asynchronous crawling capabilities. The crawl is started
with one call, and you check status with another.

WHEN TO USE:
- You need to scrape many pages from a website
- You want to follow links and scrape recursively
- The crawl may take a long time

USE FIRECRAWL_SCRAPE INSTEAD WHEN:
- You only need one or a few specific pages
- You know the exact URLs you want

WORKFLOW:
1. Call firecrawl_crawl to start the job (returns job ID)
2. Call firecrawl_check_crawl_status with the job ID to check progress
3. Status will include results when complete

=============================================================================
"""

from typing import Any, Dict
from datetime import datetime
from langchain_core.tools import tool

from tools.mcp.base import MCPTool
from . import FIRECRAWL_MCP_URL


class FirecrawlCrawlTool(MCPTool):
    """
    Tool for starting asynchronous crawl jobs using Firecrawl MCP.
    
    This tool starts a crawl job that will recursively scrape pages from
    a website. The crawl runs asynchronously - use firecrawl_check_crawl_status
    to monitor progress and get results.
    
    Features:
        - Recursive crawling with depth control
        - Page limit to control crawl scope
        - Option to follow external links
        - Asynchronous execution
    
    Example Usage:
        ```python
        # Start a crawl
        tool = FirecrawlCrawlTool()
        result = await tool.execute(
            url="https://docs.example.com",
            maxDepth=2,
            limit=50
        )
        # result contains the job ID
        
        # Check status with FirecrawlCheckCrawlStatusTool
        status_tool = FirecrawlCheckCrawlStatusTool()
        status = await status_tool.execute(id=job_id)
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_crawl"
    description = "Start an asynchronous crawl job with advanced options. Returns a job ID for status checking."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the crawl tool."""
        return {
            "url": {
                "type": "string",
                "required": True,
                "description": "URL to start crawling from. The crawler will discover and scrape linked pages."
            },
            "maxDepth": {
                "type": "integer",
                "required": False,
                "default": 2,
                "description": "Maximum depth to crawl (number of link hops from start URL). Default: 2"
            },
            "limit": {
                "type": "integer",
                "required": False,
                "default": 100,
                "description": "Maximum number of pages to crawl. Default: 100"
            },
            "allowExternalLinks": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "If true, follows links to external domains. Default: false"
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_crawl(
            url: str,
            maxDepth: int = 2,
            limit: int = 100,
            allowExternalLinks: bool = False
        ) -> str:
            """
            Start an asynchronous crawl job.
            
            Use this tool when you need to scrape multiple pages from a website.
            The crawl runs in the background - use firecrawl_check_crawl_status
            with the returned job ID to check progress and get results.
            
            Args:
                url: URL to start crawling from
                maxDepth: Maximum crawl depth (default: 2)
                limit: Maximum pages to crawl (default: 100)
                allowExternalLinks: Follow external links (default: false)
            
            Returns:
                Crawl job ID for status checking
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_crawl
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from crawl job initiation."""
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "crawl_job",
            "start_url": tool_args.get("url", ""),
            "max_depth": tool_args.get("maxDepth", 2),
            "page_limit": tool_args.get("limit", 100),
        }


class FirecrawlCheckCrawlStatusTool(MCPTool):
    """
    Tool for checking the status of a crawl job using Firecrawl MCP.
    
    After starting a crawl with firecrawl_crawl, use this tool to check
    if the crawl is complete and get the results.
    
    Status Values:
        - "pending": Job is queued
        - "running": Crawl is in progress
        - "completed": Crawl finished successfully (results included)
        - "failed": Crawl failed (error message included)
    
    Example Usage:
        ```python
        tool = FirecrawlCheckCrawlStatusTool()
        result = await tool.execute(id="crawl_job_abc123")
        # Returns status and results if complete
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_check_crawl_status"
    description = "Check the status of a crawl job. Returns status and results when complete."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the check status tool."""
        return {
            "id": {
                "type": "string",
                "required": True,
                "description": "Crawl job ID returned from firecrawl_crawl."
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_check_crawl_status(id: str) -> str:
            """
            Check the status of a crawl job.
            
            Use this tool after starting a crawl with firecrawl_crawl to
            check if it's complete and get the results.
            
            Args:
                id: Crawl job ID returned from firecrawl_crawl
            
            Returns:
                Status and progress of the crawl job, results if complete
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_check_crawl_status
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from crawl status check."""
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "crawl_status",
            "job_id": tool_args.get("id", ""),
        }
