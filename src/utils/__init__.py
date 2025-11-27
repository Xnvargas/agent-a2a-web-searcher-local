"""
=============================================================================
UTILS PACKAGE - Agent Factory and Utilities
=============================================================================

This package provides utilities for creating LangGraph agents and citation
handling.

MAIN EXPORTS:
-------------

- create_langgraph_agent: Factory function to create agents with tools

USAGE:
------

```python
from utils import create_langgraph_agent
from tools import get_all_tools

# Create agent with all registered tools
agent = create_langgraph_agent(
    api_model="granite-4:micro-h",
    api_key="your-key",
    api_base="http://localhost:11434/v1",
    tools=get_all_tools()
)

# Or create with specific tools
from tools import get_tool_by_name
custom_tools = [
    get_tool_by_name("firecrawl_scrape"),
    get_tool_by_name("searx_search"),
]
agent = create_langgraph_agent(..., tools=custom_tools)
```

=============================================================================
"""

# -----------------------------------------------------------------------------
# Main factory function
# -----------------------------------------------------------------------------
from .langgraph_factory import create_langgraph_agent

# -----------------------------------------------------------------------------
# Citation utilities (optional)
# -----------------------------------------------------------------------------
from .citations import (
    format_citation,
    format_citations_for_beeai,
    format_tool_data_for_logging,
    print_tool_execution,
)

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
__all__ = [
    # Factory
    "create_langgraph_agent",
    
    # Citations
    "format_citation",
    "format_citations_for_beeai",
    "format_tool_data_for_logging",
    "print_tool_execution",
]
