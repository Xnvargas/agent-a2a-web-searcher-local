"""
=============================================================================
TAVILY TOOLS - AI-Optimized Web Search
=============================================================================

This package provides tools for searching the web using Tavily, an
AI-optimized search engine designed specifically for LLM agents.

AVAILABLE TOOLS:
----------------

1. tavily_search - Search the web with AI-optimized results


WHAT IS TAVILY?
---------------

Tavily is a search engine purpose-built for AI agents that:
- Returns results optimized for LLM consumption
- Provides comprehensive content snippets
- Offers optional AI-generated answers
- Supports basic and advanced search depths


CONFIGURATION:
--------------

Set your Tavily API key via environment variable:

    export TAVILY_API_KEY="your-api-key-here"

Get your API key at: https://tavily.com

Optional settings:
    export TAVILY_MAX_RESULTS="5"      # Default max results
    export TAVILY_SEARCH_DEPTH="basic"  # basic or advanced


USAGE:
------

```python
from tools.langchain.tavily import TavilySearchTool

tool = TavilySearchTool()
result = await tool.execute(
    query="latest AI developments",
    max_results=5,
    search_depth="basic"
)
```

=============================================================================
"""

import os

# -----------------------------------------------------------------------------
# CONFIGURATION
# Override via environment variables
# -----------------------------------------------------------------------------

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
"""
Tavily API key. Required for all Tavily operations.
Get your key at: https://tavily.com
"""

TAVILY_DEFAULT_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "5"))
"""
Default number of search results to return.
Override with TAVILY_MAX_RESULTS environment variable.
"""

TAVILY_DEFAULT_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic")
"""
Default search depth: 'basic' or 'advanced'.
Override with TAVILY_SEARCH_DEPTH environment variable.
"""

# -----------------------------------------------------------------------------
# Import and register tools
# -----------------------------------------------------------------------------

from tools.registry import ToolRegistry
from .search import TavilySearchTool

# Register the tool (only if API key is available)
if TAVILY_API_KEY:
    ToolRegistry.register(TavilySearchTool())
    print(f"✅ Registered Tavily search tool")
else:
    print(f"⚠️ Tavily tool not registered: TAVILY_API_KEY not set")

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    "TAVILY_API_KEY",
    "TAVILY_DEFAULT_MAX_RESULTS",
    "TAVILY_DEFAULT_SEARCH_DEPTH",
    "TavilySearchTool",
]
