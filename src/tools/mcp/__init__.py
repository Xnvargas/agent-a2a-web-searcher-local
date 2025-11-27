"""
=============================================================================
MCP TOOLS PACKAGE - Model Context Protocol Based Tools
=============================================================================

This package contains tools that execute via the Model Context Protocol (MCP).
MCP tools communicate with external servers via JSON-RPC over HTTP.

WHAT IS MCP?
------------

The Model Context Protocol is a standard for AI agents to interact with
external services. MCP servers expose tools via a JSON-RPC API that follows
a specific protocol for:
- Tool discovery (list available tools)
- Tool execution (call tools with arguments)
- Result streaming (handle large responses)

MCP TOOL ARCHITECTURE:
----------------------

    tools/mcp/
    ├── __init__.py      # This file - package exports
    ├── base.py          # MCPTool base class (extend this)
    ├── client.py        # MCPClient HTTP client for MCP communication
    └── firecrawl/       # Example: Firecrawl MCP tools
        ├── __init__.py  # Registers Firecrawl tools
        ├── scrape.py    # Individual tool files
        ├── map.py
        └── ...

HOW TO ADD A NEW MCP SERVICE:
-----------------------------

1. Create a directory for your service: tools/mcp/your_service/
2. Create tool files extending MCPTool (see base.py for details)
3. Create __init__.py to register your tools
4. Import in tools/mcp/__init__.py to trigger registration

Example - Adding GitHub MCP tools:

1. Create tools/mcp/github/create_issue.py:
   ```python
   from tools.mcp.base import MCPTool
   
   class GitHubCreateIssueTool(MCPTool):
       name = "github_create_issue"
       description = "Create a GitHub issue"
       mcp_server_url = "http://localhost:3001/mcp"
       
       def get_schema(self) -> dict:
           return {
               "repo": {"type": "string", "required": True},
               "title": {"type": "string", "required": True},
               "body": {"type": "string", "required": False}
           }
   ```

2. Create tools/mcp/github/__init__.py:
   ```python
   from tools.registry import ToolRegistry
   from .create_issue import GitHubCreateIssueTool
   
   ToolRegistry.register(GitHubCreateIssueTool())
   ```

3. Add to tools/mcp/__init__.py:
   ```python
   from . import github  # Triggers registration
   ```

=============================================================================
"""

# -----------------------------------------------------------------------------
# MCP Infrastructure
# -----------------------------------------------------------------------------
from .base import MCPTool
from .client import MCPClient, get_mcp_client

# -----------------------------------------------------------------------------
# Import MCP service packages to trigger tool registration
# Add new MCP services here
# -----------------------------------------------------------------------------

# Firecrawl MCP - Web scraping tools
from . import firecrawl

# -----------------------------------------------------------------------------
# ADD NEW MCP SERVICES HERE:
# Example:
# from . import github    # GitHub MCP tools
# from . import slack     # Slack MCP tools  
# from . import notion    # Notion MCP tools
# -----------------------------------------------------------------------------

__all__ = [
    "MCPTool",
    "MCPClient", 
    "get_mcp_client",
]
