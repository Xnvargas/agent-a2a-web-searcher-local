"""
=============================================================================
FIRECRAWL MCP TOOLS - Web Scraping and Crawling via Firecrawl MCP Server
=============================================================================

This package provides tools for interacting with the Firecrawl MCP server,
enabling web scraping, crawling, and content extraction capabilities.

AVAILABLE TOOLS:
----------------

1. firecrawl_scrape    - Scrape content from a single URL
2. firecrawl_map       - Map a website to discover URLs
3. firecrawl_search    - Search the web with content extraction
4. firecrawl_extract   - Extract structured data using LLM
5. firecrawl_crawl     - Start async crawl job
6. firecrawl_check_crawl_status  - Check crawl job status
7. firecrawl_batch_scrape        - Batch scrape multiple URLs
8. firecrawl_check_batch_status  - Check batch job status


CONFIGURATION:
--------------

Set the Firecrawl MCP server URL via environment variable:

    export FIRECRAWL_MCP_URL="http://your-firecrawl-server:3123/mcp"

Default: http://192.168.0.229:3123/mcp


USAGE:
------

Tools are automatically registered when this package is imported.
Use via the agent or directly:

```python
from tools.mcp.firecrawl import FirecrawlScrapeTool

tool = FirecrawlScrapeTool()
result = await tool.execute(url="https://example.com")
```

=============================================================================
"""

import os

# -----------------------------------------------------------------------------
# CONFIGURATION
# Override via environment variables
# Must be defined BEFORE importing tool classes that use them
# -----------------------------------------------------------------------------

FIRECRAWL_MCP_URL = os.getenv("FIRECRAWL_MCP_URL", "http://192.168.0.229:3123/mcp")
"""
URL of the Firecrawl MCP server.
Override with FIRECRAWL_MCP_URL environment variable.
"""

FIRECRAWL_SERVER_NAME = "firecrawl"
"""
Name identifier for the Firecrawl MCP server.
Used for logging and debugging.
"""

# -----------------------------------------------------------------------------
# Import and register all Firecrawl tools
# NOTE: Tools import FIRECRAWL_MCP_URL from this module, so config must be above
# -----------------------------------------------------------------------------

from tools.registry import ToolRegistry

# Import tool classes (they import FIRECRAWL_MCP_URL from this module)
from .scrape import FirecrawlScrapeTool
from .map import FirecrawlMapTool
from .search import FirecrawlSearchTool
from .extract import FirecrawlExtractTool
from .crawl import FirecrawlCrawlTool, FirecrawlCheckCrawlStatusTool
from .batch import FirecrawlBatchScrapeTool, FirecrawlCheckBatchStatusTool

# Register all tools
# Comment out any tools you don't want to expose to the agent
ToolRegistry.register(FirecrawlScrapeTool())
ToolRegistry.register(FirecrawlMapTool())
ToolRegistry.register(FirecrawlSearchTool())
ToolRegistry.register(FirecrawlExtractTool())
ToolRegistry.register(FirecrawlCrawlTool())
ToolRegistry.register(FirecrawlCheckCrawlStatusTool())
ToolRegistry.register(FirecrawlBatchScrapeTool())
ToolRegistry.register(FirecrawlCheckBatchStatusTool())

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    # Configuration
    "FIRECRAWL_MCP_URL",
    "FIRECRAWL_SERVER_NAME",
    
    # Tools
    "FirecrawlScrapeTool",
    "FirecrawlMapTool",
    "FirecrawlSearchTool",
    "FirecrawlExtractTool",
    "FirecrawlCrawlTool",
    "FirecrawlCheckCrawlStatusTool",
    "FirecrawlBatchScrapeTool",
    "FirecrawlCheckBatchStatusTool",
]
