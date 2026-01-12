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
# Main factory function - LangGraph
# -----------------------------------------------------------------------------
from .langgraph_factory import create_langgraph_agent
from .content_parts import (
    ContentType,
    TypedContent,
    ToolCallInfo,
    ToolResultInfo,
    create_thinking_metadata,
    create_response_metadata,
    create_tool_call_metadata,
    create_tool_result_metadata,
    create_status_metadata,
    format_thinking_trajectory,
    format_tool_call_trajectory,
    format_tool_result_trajectory,
)

# -----------------------------------------------------------------------------
# BeeAI Framework factory function
# -----------------------------------------------------------------------------
from .bee_factory import (
    create_beeai_agent,
    create_beeai_llm,
    wrap_tools_for_beeai,
    run_beeai_agent,
)

# -----------------------------------------------------------------------------
# Citation utilities (LangGraph)
# -----------------------------------------------------------------------------
from .citations import (
    format_citation,
    format_citations_for_beeai,
    format_tool_data_for_logging,
    print_tool_execution,
)

# -----------------------------------------------------------------------------
# BeeAI Citation utilities
# -----------------------------------------------------------------------------
from .bee_citations import (
    format_bee_citation,
    format_bee_citations_for_beeai,
    format_bee_tool_data_for_logging,
    print_bee_tool_execution,
    extract_bee_citations_from_response,
)

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
__all__ = [
    # LangGraph Factory
    "create_langgraph_agent",
    
    # BeeAI Factory
    "create_beeai_agent",
    "create_beeai_llm",
    "wrap_tools_for_beeai",
    "run_beeai_agent",
    
    # LangGraph Citations
    "format_citation",
    "format_citations_for_beeai",
    "format_tool_data_for_logging",
    "print_tool_execution",
    
    # BeeAI Citations
    "format_bee_citation",
    "format_bee_citations_for_beeai",
    "format_bee_tool_data_for_logging",
    "print_bee_tool_execution",
    "extract_bee_citations_from_response",
]
