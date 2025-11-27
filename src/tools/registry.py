"""
=============================================================================
TOOL REGISTRY - Central Management System for Tools
=============================================================================

This module provides a centralized registry for managing tool instances.
Tools register themselves with the registry, and the agent factory queries
the registry to get all available tools.

DESIGN PATTERN:
--------------

The registry uses explicit registration rather than auto-discovery for:
1. Clarity: You can see exactly what tools are registered in each __init__.py
2. Simplicity: No magic scanning of directories
3. Control: Easy to enable/disable tools by commenting out registration
4. Type Safety: IDE can track tool references

HOW TOOL REGISTRATION WORKS:
----------------------------

1. Each tool package (e.g., tools/mcp/firecrawl/__init__.py) imports its tools
2. The package calls ToolRegistry.register(ToolInstance())
3. When tools/__init__.py imports the package, registration happens
4. The agent factory calls get_all_tools() to get registered tools

EXAMPLE - Adding a new tool package:
------------------------------------

In tools/mcp/github/__init__.py:
```python
from tools.registry import ToolRegistry
from .create_issue import GitHubCreateIssueTool
from .list_repos import GitHubListReposTool

# Register tools when this package is imported
ToolRegistry.register(GitHubCreateIssueTool())
ToolRegistry.register(GitHubListReposTool())
```

Then in tools/__init__.py, add:
```python
from .mcp import github  # Triggers registration
```

=============================================================================
"""

from typing import Dict, List, Optional, TYPE_CHECKING

# Avoid circular import - BaseTool is only used for type hints
if TYPE_CHECKING:
    from .base import BaseTool


class ToolRegistry:
    """
    Central registry for managing tool instances.
    
    This is a class-level (static) registry - there's only one registry
    shared across the entire application. Tools register themselves when
    their packages are imported.
    
    Class Attributes:
        _tools (Dict[str, BaseTool]): Map of tool name -> tool instance
        _initialized (bool): Whether the registry has been accessed
    
    Usage:
        ```python
        # Register a tool (usually in tool package __init__.py)
        from tools.registry import ToolRegistry
        ToolRegistry.register(MyTool())
        
        # Get all tools (in agent factory)
        tools = ToolRegistry.get_all_tools()
        
        # Get specific tool by name
        tool = ToolRegistry.get_tool("firecrawl_scrape")
        ```
    
    Thread Safety:
        The registry is not thread-safe by design. Tool registration happens
        at import time before any concurrent execution begins.
    """
    
    # -------------------------------------------------------------------------
    # Class-level storage - shared across all instances
    # -------------------------------------------------------------------------
    
    _tools: Dict[str, "BaseTool"] = {}
    """
    Map of tool name -> tool instance.
    Keys are tool names (e.g., "firecrawl_scrape").
    Values are BaseTool instances (MCPTool, LangChainTool, etc.).
    """
    
    _initialized: bool = False
    """
    Tracks whether the registry has been accessed.
    Used for debugging and logging purposes.
    """
    
    # -------------------------------------------------------------------------
    # Registration methods - Called by tool packages
    # -------------------------------------------------------------------------
    
    @classmethod
    def register(cls, tool: "BaseTool") -> None:
        """
        Register a tool instance with the registry.
        
        Called by tool packages during import to make their tools available
        to the agent. Duplicate registrations (same tool name) will log a
        warning and overwrite the existing tool.
        
        Args:
            tool: An instance of a class extending BaseTool
        
        Example:
            ```python
            # In tools/mcp/firecrawl/__init__.py
            from tools.registry import ToolRegistry
            from .scrape import FirecrawlScrapeTool
            
            ToolRegistry.register(FirecrawlScrapeTool())
            ```
        
        Validation:
            - Checks that tool.name is not empty
            - Warns on duplicate registrations (allows override)
        """
        if not tool.name:
            raise ValueError(
                f"Cannot register tool {tool.__class__.__name__}: "
                f"'name' attribute is empty. Set a unique name."
            )
        
        if tool.name in cls._tools:
            # Allow override but warn in logs
            print(
                f"⚠️  ToolRegistry: Overwriting existing tool '{tool.name}' "
                f"({cls._tools[tool.name].__class__.__name__} -> {tool.__class__.__name__})"
            )
        
        cls._tools[tool.name] = tool
        print(f"✓ ToolRegistry: Registered '{tool.name}' ({tool.__class__.__name__})")
    
    @classmethod
    def unregister(cls, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Useful for testing or dynamic tool management. Returns True if
        the tool was found and removed, False otherwise.
        
        Args:
            tool_name: Name of the tool to remove
        
        Returns:
            bool: True if tool was removed, False if not found
        
        Example:
            ```python
            ToolRegistry.unregister("firecrawl_scrape")
            ```
        """
        if tool_name in cls._tools:
            del cls._tools[tool_name]
            print(f"✓ ToolRegistry: Unregistered '{tool_name}'")
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """
        Remove all tools from the registry.
        
        Primarily used for testing. Resets the registry to empty state.
        
        Example:
            ```python
            # In tests
            ToolRegistry.clear()
            assert len(ToolRegistry.get_all_tools()) == 0
            ```
        """
        cls._tools.clear()
        cls._initialized = False
        print("✓ ToolRegistry: Cleared all tools")
    
    # -------------------------------------------------------------------------
    # Query methods - Called by agent factory and other consumers
    # -------------------------------------------------------------------------
    
    @classmethod
    def get_all_tools(cls) -> List["BaseTool"]:
        """
        Get all registered tool instances.
        
        Returns a list of all tools that have been registered. The order
        is not guaranteed (dict iteration order in Python 3.7+).
        
        Returns:
            List[BaseTool]: List of all registered tool instances
        
        Example:
            ```python
            tools = ToolRegistry.get_all_tools()
            for tool in tools:
                print(f"{tool.name}: {tool.description}")
            ```
        """
        cls._initialized = True
        return list(cls._tools.values())
    
    @classmethod
    def get_tool(cls, tool_name: str) -> Optional["BaseTool"]:
        """
        Get a specific tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
        
        Returns:
            Optional[BaseTool]: Tool instance if found, None otherwise
        
        Example:
            ```python
            scrape_tool = ToolRegistry.get_tool("firecrawl_scrape")
            if scrape_tool:
                result = await scrape_tool.execute(url="https://example.com")
            ```
        """
        cls._initialized = True
        return cls._tools.get(tool_name)
    
    @classmethod
    def get_tools_by_type(cls, tool_type: str) -> List["BaseTool"]:
        """
        Get all tools of a specific type.
        
        Useful for filtering tools by execution method (e.g., only MCP tools
        or only LangChain tools).
        
        Args:
            tool_type: Type to filter by ("mcp", "langchain", etc.)
        
        Returns:
            List[BaseTool]: List of tools matching the type
        
        Example:
            ```python
            # Get only MCP-based tools
            mcp_tools = ToolRegistry.get_tools_by_type("mcp")
            
            # Get only LangChain tools
            langchain_tools = ToolRegistry.get_tools_by_type("langchain")
            ```
        """
        return [
            tool for tool in cls._tools.values() 
            if tool.tool_type == tool_type
        ]
    
    @classmethod
    def get_tool_names(cls) -> List[str]:
        """
        Get a list of all registered tool names.
        
        Useful for debugging and logging.
        
        Returns:
            List[str]: List of tool names
        
        Example:
            ```python
            names = ToolRegistry.get_tool_names()
            # ['firecrawl_scrape', 'firecrawl_map', 'searx_search', ...]
            ```
        """
        return list(cls._tools.keys())
    
    @classmethod
    def is_registered(cls, tool_name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            tool_name: Name to check
        
        Returns:
            bool: True if tool is registered
        
        Example:
            ```python
            if ToolRegistry.is_registered("firecrawl_scrape"):
                print("Firecrawl scrape is available")
            ```
        """
        return tool_name in cls._tools
    
    @classmethod
    def count(cls) -> int:
        """
        Get the number of registered tools.
        
        Returns:
            int: Number of registered tools
        """
        return len(cls._tools)
    
    # -------------------------------------------------------------------------
    # Information methods - For debugging and introspection
    # -------------------------------------------------------------------------
    
    @classmethod
    def print_registry(cls) -> None:
        """
        Print a summary of all registered tools.
        
        Useful for debugging and verifying tool registration.
        
        Example Output:
            ```
            ToolRegistry Contents (6 tools):
            --------------------------------
            1. firecrawl_scrape (MCPTool) - Scrape content from a URL
            2. firecrawl_map (MCPTool) - Map website URLs
            3. searx_search (LangChainTool) - Search using SearxNG
            ...
            ```
        """
        print(f"\nToolRegistry Contents ({cls.count()} tools):")
        print("-" * 40)
        
        for idx, (name, tool) in enumerate(cls._tools.items(), 1):
            tool_class = tool.__class__.__name__
            desc_preview = tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
            print(f"{idx}. {name} ({tool_class}) - {desc_preview}")
        
        print("-" * 40)


# =============================================================================
# Module-level convenience functions
# =============================================================================

def get_all_tools() -> List["BaseTool"]:
    """
    Convenience function to get all registered tools.
    
    Same as ToolRegistry.get_all_tools() but available at module level.
    
    Returns:
        List[BaseTool]: All registered tools
    
    Example:
        ```python
        from tools import get_all_tools
        tools = get_all_tools()
        ```
    """
    return ToolRegistry.get_all_tools()


def get_tool_by_name(tool_name: str) -> Optional["BaseTool"]:
    """
    Convenience function to get a tool by name.
    
    Same as ToolRegistry.get_tool() but available at module level.
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Optional[BaseTool]: Tool instance or None
    
    Example:
        ```python
        from tools import get_tool_by_name
        scrape = get_tool_by_name("firecrawl_scrape")
        ```
    """
    return ToolRegistry.get_tool(tool_name)
