"""
=============================================================================
LANGCHAIN TOOL BASE CLASS - Base for Native Python Tools
=============================================================================

This module provides the LangChainTool abstract base class that all native
Python tools should extend. Unlike MCP tools, LangChain tools execute their
logic directly in the agent process.

WHEN TO USE LANGCHAIN TOOLS:
----------------------------

Use LangChainTool when:
- You're wrapping an existing Python library (e.g., langchain-community)
- The tool is a simple operation that doesn't need external services
- You want tighter integration with Python code
- You need to use async Python libraries directly

Use MCPTool instead when:
- The tool is provided by an external MCP server
- You want to share the tool across multiple agents
- The tool needs to run in a separate process/container


WHAT TO IMPLEMENT:
------------------

1. Set class attributes:
   - name: Unique tool name
   - description: What the tool does

2. Implement required methods:
   - get_schema(): Define parameters
   - execute(): Your Python implementation
   - get_langchain_tool(): Return @tool decorated function


MINIMAL EXAMPLE:
----------------

```python
from tools.langchain.base import LangChainTool
from langchain_core.tools import tool

class CalculatorTool(LangChainTool):
    name = "calculator"
    description = "Perform basic math calculations"
    
    def get_schema(self) -> dict:
        return {
            "expression": {
                "type": "string",
                "required": True,
                "description": "Math expression to evaluate"
            }
        }
    
    async def execute(self, expression: str) -> str:
        try:
            result = eval(expression)  # Note: use proper parser in production!
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_langchain_tool(self):
        @tool
        def calculator(expression: str) -> str:
            '''Perform basic math calculations'''
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return calculator
```


FULL EXAMPLE WITH API CALL:
---------------------------

```python
import os
import httpx
from tools.langchain.base import LangChainTool
from langchain_core.tools import tool
from datetime import datetime

class WeatherTool(LangChainTool):
    name = "get_weather"
    description = "Get current weather for a city"
    
    # Configuration
    api_base_url = os.getenv("WEATHER_API_URL", "https://api.weather.com")
    api_key = os.getenv("WEATHER_API_KEY", "")
    
    def get_schema(self) -> dict:
        return {
            "city": {
                "type": "string",
                "required": True,
                "description": "City name to get weather for"
            },
            "units": {
                "type": "string",
                "required": False,
                "default": "celsius",
                "description": "Temperature units (celsius/fahrenheit)"
            }
        }
    
    async def execute(self, city: str, units: str = "celsius") -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/weather",
                params={"city": city, "units": units, "key": self.api_key}
            )
            
            if response.status_code != 200:
                return f"Error: Weather API returned {response.status_code}"
            
            data = response.json()
            return f"Weather in {city}: {data['temp']}° {units}, {data['conditions']}"
    
    def get_langchain_tool(self):
        @tool
        def get_weather(city: str, units: str = "celsius") -> str:
            '''Get current weather for a city'''
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_weather
    
    def get_citation_metadata(self, tool_args, tool_result):
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "api",
            "api": "weather_api",
            "city": tool_args.get("city", ""),
        }
```

=============================================================================
"""

from abc import abstractmethod
from typing import Any, Dict, Callable
from datetime import datetime

from ..base import BaseTool


class LangChainTool(BaseTool):
    """
    Abstract base class for native Python/LangChain tools.
    
    LangChainTool extends BaseTool for tools that execute their logic
    directly in Python, without needing an external MCP server.
    
    Key Differences from MCPTool:
    - No mcp_server_url - logic runs locally
    - execute() must be fully implemented by you
    - Simpler for wrapping Python libraries
    
    Subclasses must implement:
    - get_schema(): Define the tool's parameters
    - execute(): The actual Python implementation
    - get_langchain_tool(): Return @tool decorated function
    
    Optionally override:
    - get_citation_metadata(): For custom citation extraction
    
    Attributes:
        name (str): Unique tool name - MUST match function name in get_langchain_tool()
        description (str): Tool description shown to LLM
        tool_type (str): Always "langchain" for LangChain tools
    
    Example:
        ```python
        class MyTool(LangChainTool):
            name = "my_tool"
            description = "Does something locally"
            
            def get_schema(self) -> dict:
                return {"param": {"type": "string", "required": True}}
            
            async def execute(self, param: str) -> str:
                # Your Python implementation here
                return f"Processed: {param}"
            
            def get_langchain_tool(self):
                @tool
                def my_tool(param: str) -> str:
                    '''Does something locally'''
                    return "PLACEHOLDER"
                return my_tool
        ```
    """
    
    # -------------------------------------------------------------------------
    # CLASS ATTRIBUTES
    # -------------------------------------------------------------------------
    
    tool_type: str = "langchain"
    """Identifies this as a LangChain tool. Do not change."""
    
    # -------------------------------------------------------------------------
    # REQUIRED ABSTRACT METHODS - You MUST implement these
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the parameter schema for this tool.
        
        See BaseTool.get_schema() for full documentation.
        
        Returns:
            Dict mapping parameter names to their configs
        
        Example:
            ```python
            def get_schema(self) -> dict:
                return {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "default": 10,
                        "description": "Max results"
                    }
                }
            ```
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool's logic.
        
        Unlike MCPTool, you MUST implement this method with your actual
        tool logic. This is where your Python code runs.
        
        Args:
            **kwargs: Tool arguments matching get_schema()
        
        Returns:
            str: Tool result as a string. For structured data, return JSON.
        
        Best Practices:
            - Return error messages as strings, don't raise exceptions
            - Use async operations where possible for I/O
            - Keep the result focused and useful for the LLM
            - Include relevant context in the result
        
        Example:
            ```python
            async def execute(self, query: str, limit: int = 10) -> str:
                try:
                    # Your implementation here
                    results = await self.search_api(query, limit)
                    return json.dumps(results)
                except Exception as e:
                    return f"Error: {str(e)}"
            ```
        """
        pass
    
    @abstractmethod
    def get_langchain_tool(self) -> Callable:
        """
        Return a LangChain @tool decorated function.
        
        The function name MUST match self.name exactly. The function body
        should return a placeholder - actual execution uses execute().
        
        Returns:
            A @tool decorated function
        
        Example:
            ```python
            def get_langchain_tool(self):
                @tool
                def searx_search(query: str, limit: int = 10) -> str:
                    '''Search the web using SearxNG'''
                    return "LANGCHAIN_TOOL_PLACEHOLDER"
                return searx_search
            ```
        
        Important Notes:
            - Function name must match self.name
            - Docstring becomes the tool description in LangChain
            - Parameter types affect JSON schema generation
            - Default values should match get_schema() defaults
        """
        pass
    
    # -------------------------------------------------------------------------
    # CITATION - Override for custom citation extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """
        Extract citation metadata from tool execution.
        
        Default implementation provides basic metadata. Override this for
        tool-specific citation extraction.
        
        Args:
            tool_args: Arguments passed to the tool
            tool_result: Result from execute()
        
        Returns:
            Citation metadata dictionary
        
        Override Example (for a search tool):
            ```python
            def get_citation_metadata(self, tool_args, tool_result):
                return {
                    "tool": self.name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source_type": "search",
                    "query": tool_args.get("query", ""),
                    "num_results": tool_args.get("limit", 10),
                }
            ```
        """
        citation = {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "langchain",
        }
        
        # Add query if present (common for search tools)
        if "query" in tool_args:
            citation["query"] = tool_args["query"]
        
        # Extract content preview
        if isinstance(tool_result, str):
            preview = tool_result[:200]
            if len(tool_result) > 200:
                preview += "..."
            citation["content_preview"] = preview
        
        return citation
