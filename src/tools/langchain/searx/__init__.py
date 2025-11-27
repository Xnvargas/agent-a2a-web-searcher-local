"""
=============================================================================
SEARXNG TOOLS - Privacy-Respecting Metasearch
=============================================================================

This package provides tools for searching the web using SearxNG, a 
privacy-respecting metasearch engine that aggregates results from multiple
search engines.

AVAILABLE TOOLS:
----------------

1. searx_search - Search the web and get structured results


WHAT IS SEARXNG?
----------------

SearxNG is a free, open-source metasearch engine that:
- Aggregates results from 70+ search engines
- Protects user privacy (no tracking)
- Can be self-hosted
- Returns structured results with sources


CONFIGURATION:
--------------

Set the SearxNG server URL via environment variable:

    export SEARX_HOST="http://your-searx-server:8888"

Default: http://192.168.0.229:8889


USAGE:
------

```python
from tools.langchain.searx import SearxSearchTool

tool = SearxSearchTool()
result = await tool.execute(query="python machine learning")
```

=============================================================================
"""

import os

# -----------------------------------------------------------------------------
# CONFIGURATION
# Override via environment variables
# -----------------------------------------------------------------------------

SEARX_HOST = os.getenv("SEARX_HOST", "http://192.168.0.229:8889")
"""
URL of the SearxNG server.
Override with SEARX_HOST environment variable.
"""

SEARX_DEFAULT_NUM_RESULTS = int(os.getenv("SEARX_NUM_RESULTS", "5"))
"""
Default number of search results to return.
Override with SEARX_NUM_RESULTS environment variable.
"""

# -----------------------------------------------------------------------------
# Import and register tools
# -----------------------------------------------------------------------------

from tools.registry import ToolRegistry
from .search import SearxSearchTool

# Register the tool
ToolRegistry.register(SearxSearchTool())

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    "SEARX_HOST",
    "SEARX_DEFAULT_NUM_RESULTS",
    "SearxSearchTool",
]
