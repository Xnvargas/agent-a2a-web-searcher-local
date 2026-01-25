"""
=============================================================================
TOOLS PACKAGE - Modular Tool Architecture for LangGraph Agents
=============================================================================

This package provides a modular, extensible architecture for adding tools to
LangGraph-based agents. Tools can be MCP-based (Model Context Protocol) or
native LangChain tools.

ARCHITECTURE OVERVIEW:
----------------------

    tools/
    ├── __init__.py          # This file - exports and tool discovery
    ├── base.py              # BaseTool abstract class (extend for custom tools)
    ├── registry.py          # ToolRegistry for managing tool instances
    ├── mcp/                  # MCP-based tools (external services via JSON-RPC)
    │   ├── base.py          # MCPTool base class (extend for MCP tools)
    │   ├── client.py        # MCPClient HTTP client
    │   └── firecrawl/       # Firecrawl MCP tools (web scraping)
    └── langchain/           # Native LangChain tools (Python implementations)
        ├── base.py          # LangChainTool base class
        └── searx/           # SearxNG search tools


HOW TO ADD A NEW TOOL:
----------------------

1. For MCP Tools (external service via JSON-RPC):
   - Create a new file in tools/mcp/<service_name>/<tool_name>.py
   - Extend MCPTool class
   - Implement get_schema() and optionally override execute()
   - Register in the service's __init__.py

2. For LangChain Tools (native Python):
   - Create a new file in tools/langchain/<service_name>/<tool_name>.py
   - Extend LangChainTool class
   - Implement get_schema() and execute()
   - Register in the service's __init__.py

3. Register your tool in the appropriate __init__.py:
   ```python
   from tools.registry import ToolRegistry
   from .your_tool import YourTool
   ToolRegistry.register(YourTool())
   ```

See base.py for full documentation on the BaseTool interface.


USAGE IN AGENT:
---------------

```python
from tools import ToolRegistry, get_all_tools

# Get all registered tools for the agent
tools = get_all_tools()

# Pass to agent factory
agent = create_langgraph_agent(
    api_model="...",
    api_key="...",
    api_base="...",
    tools=tools
)
```

=============================================================================
"""

# -----------------------------------------------------------------------------
# Core exports - Base classes for extending
# -----------------------------------------------------------------------------
from .base import BaseTool
from .registry import ToolRegistry, get_all_tools, get_tool_by_name

# -----------------------------------------------------------------------------
# MCP tool infrastructure
# -----------------------------------------------------------------------------
from .mcp.base import MCPTool
from .mcp.client import MCPClient, get_mcp_client

# -----------------------------------------------------------------------------
# LangChain tool infrastructure
# -----------------------------------------------------------------------------
from .langchain.base import LangChainTool

# -----------------------------------------------------------------------------
# Import tool packages to trigger registration
# When a tool package is imported, it registers its tools with the registry.
# Add new tool package imports here after creating them.
# -----------------------------------------------------------------------------

# MCP Tools - Import to register
from .mcp import firecrawl  # Registers all Firecrawl tools

# LangChain Tools - Import to register

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
__all__ = [
    # Base classes for creating new tools
    "BaseTool",
    "MCPTool",
    "LangChainTool",
    
    # Registry for tool management
    "ToolRegistry",
    "get_all_tools",
    "get_tool_by_name",
    
    # MCP client for MCP-based tools
    "MCPClient",
    "get_mcp_client",
]
