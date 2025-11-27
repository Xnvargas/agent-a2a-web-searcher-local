"""
=============================================================================
BASE TOOL - Abstract Base Class for All Tools
=============================================================================

This module defines the BaseTool abstract class that ALL tools must inherit from,
whether they are MCP-based tools or native LangChain tools.

EXTENSION POINTS:
-----------------

To create a new tool, extend this class and implement:

1. REQUIRED - Class attributes:
   - name: str           - Unique identifier for the tool
   - description: str    - Human-readable description (shown to LLM)

2. REQUIRED - Methods:
   - get_schema()        - Return parameter definitions
   - execute(**kwargs)   - Execute the tool and return result
   - get_langchain_tool() - Return LangChain @tool decorated function

3. OPTIONAL - Override for custom behavior:
   - get_citation_metadata() - Extract citation info from results
   - validate_args()         - Custom argument validation

EXAMPLE:
--------

```python
from tools.base import BaseTool
from langchain_core.tools import tool

class MyCustomTool(BaseTool):
    name = "my_tool"
    description = "Does something useful"
    
    def get_schema(self) -> dict:
        return {
            "param1": {"type": "string", "required": True, "description": "First param"},
            "param2": {"type": "integer", "required": False, "default": 10}
        }
    
    async def execute(self, param1: str, param2: int = 10) -> str:
        # Your implementation here
        return f"Result: {param1}, {param2}"
    
    def get_langchain_tool(self):
        @tool
        def my_tool(param1: str, param2: int = 10) -> str:
            '''Does something useful'''
            return "TOOL_PLACEHOLDER"
        return my_tool
```

=============================================================================
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from datetime import datetime


class BaseTool(ABC):
    """
    Abstract base class for all tools in the agent system.
    
    This class defines the interface that all tools must implement to be
    usable by the LangGraph agent. Tools can be:
    
    - MCP Tools: Execute via JSON-RPC to external MCP servers (see MCPTool)
    - LangChain Tools: Execute locally via Python (see LangChainTool)
    
    Attributes:
        name (str): Unique identifier for the tool. Must match the function name
                   in get_langchain_tool(). Used for tool routing in tool_node.
        
        description (str): Human-readable description shown to the LLM. Should
                          clearly explain what the tool does and when to use it.
        
        tool_type (str): Category of tool execution. Set by subclasses:
                        - "mcp": Executed via MCP JSON-RPC protocol
                        - "langchain": Executed locally via Python
    
    Methods to Implement:
        get_schema(): Define the parameters this tool accepts
        execute(): The actual tool implementation
        get_langchain_tool(): Return a @tool decorated function for LangChain
    
    Optional Overrides:
        get_citation_metadata(): Customize citation extraction
        validate_args(): Add custom argument validation
    """
    
    # -------------------------------------------------------------------------
    # REQUIRED: Class attributes - Override these in your tool class
    # -------------------------------------------------------------------------
    
    name: str = ""
    """
    Unique identifier for this tool.
    
    IMPORTANT: This must match the function name returned by get_langchain_tool().
    The tool_node uses this name to route execution to the correct handler.
    
    Naming Convention:
    - Use snake_case: 'my_tool_name'
    - Prefix with service name for MCP tools: 'firecrawl_scrape', 'github_create_issue'
    - Be descriptive but concise
    
    Example: name = "firecrawl_scrape"
    """
    
    description: str = ""
    """
    Human-readable description of what this tool does.
    
    This description is shown to the LLM when it's deciding which tool to use.
    Make it clear and actionable. Include:
    - What the tool does
    - When to use it (vs other tools)
    - What kind of output to expect
    
    Example: description = "Scrape content from a URL and return as markdown."
    """
    
    tool_type: str = "base"
    """
    Category of tool execution. Set automatically by subclasses:
    - "mcp": Tool executes via MCP JSON-RPC protocol to external server
    - "langchain": Tool executes locally via Python code
    
    Do not override this directly - extend MCPTool or LangChainTool instead.
    """
    
    # -------------------------------------------------------------------------
    # REQUIRED: Abstract methods - You MUST implement these
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the parameter schema for this tool.
        
        The schema defines what arguments the tool accepts. Each parameter
        is a key-value pair where the key is the parameter name and the
        value is a dictionary with:
        
        - type (str): Parameter type - "string", "integer", "boolean", "array", "object"
        - required (bool): Whether this parameter is required
        - description (str): What this parameter does
        - default (Any): Optional default value if not required
        
        Returns:
            Dict[str, Dict[str, Any]]: Parameter schema dictionary
        
        Example:
            ```python
            def get_schema(self) -> dict:
                return {
                    "url": {
                        "type": "string",
                        "required": True,
                        "description": "The URL to scrape"
                    },
                    "format": {
                        "type": "string",
                        "required": False,
                        "default": "markdown",
                        "description": "Output format"
                    },
                    "timeout": {
                        "type": "integer",
                        "required": False,
                        "default": 30000,
                        "description": "Timeout in milliseconds"
                    }
                }
            ```
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool with the given arguments.
        
        This is where your tool's logic lives. For MCP tools, this typically
        calls the MCP server. For LangChain tools, this contains the Python
        implementation.
        
        Args:
            **kwargs: Tool arguments matching the schema from get_schema()
        
        Returns:
            str: Tool execution result. Always return a string that the LLM
                 can understand and use. For structured data, return JSON string.
        
        Raises:
            Exception: Any exception will be caught and returned as an error
                      message to the LLM.
        
        Example:
            ```python
            async def execute(self, url: str, format: str = "markdown") -> str:
                # Your implementation here
                result = await some_api_call(url, format)
                return json.dumps(result)
            ```
        
        Error Handling:
            - Return error messages as strings, don't raise exceptions
            - Be descriptive: "Error: URL not accessible (404)"
            - The LLM will see the error and can decide what to do
        """
        pass
    
    @abstractmethod
    def get_langchain_tool(self) -> Callable:
        """
        Return a LangChain @tool decorated function for this tool.
        
        This function is used by LangChain's tool binding system. The function
        signature should match the schema from get_schema(). The function body
        should return a placeholder string - actual execution happens via execute().
        
        IMPORTANT: The function name MUST match self.name
        
        Returns:
            Callable: A @tool decorated function
        
        Example:
            ```python
            def get_langchain_tool(self):
                @tool
                def my_tool(url: str, format: str = "markdown") -> str:
                    '''Scrape content from a URL and return as markdown.'''
                    return "TOOL_PLACEHOLDER"
                return my_tool
            ```
        
        Why Placeholder?
        ----------------
        The @tool decorator is used by LangChain to:
        1. Extract the function signature for the LLM
        2. Generate the tool's JSON schema
        3. Bind the tool to the LLM for function calling
        
        The actual execution happens in execute(), not in this function.
        The tool_node in LangGraph intercepts tool calls and routes them
        to the appropriate execute() method.
        """
        pass
    
    # -------------------------------------------------------------------------
    # OPTIONAL: Override these for custom behavior
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """
        Extract citation metadata from tool execution.
        
        Citations are used to track the source of information returned by tools.
        Override this method to customize citation extraction for your tool.
        
        Args:
            tool_args: Arguments that were passed to the tool
            tool_result: Result returned by execute()
        
        Returns:
            Dict[str, Any]: Citation metadata dictionary with at least:
                - tool (str): Name of the tool
                - timestamp (str): ISO format timestamp
                - source_type (str): Type of source ("web_scrape", "api", etc.)
                
                You can add any additional fields relevant to your tool:
                - url (str): Source URL
                - title (str): Page/resource title
                - search_query (str): Query used for search tools
                - content_preview (str): First 200 chars of content
        
        Example:
            ```python
            def get_citation_metadata(self, tool_args, tool_result):
                return {
                    "tool": self.name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source_type": "web_scrape",
                    "url": tool_args.get("url", ""),
                    "content_preview": str(tool_result)[:200]
                }
            ```
        """
        # Default implementation - override for tool-specific citations
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": self.tool_type,
        }
    
    def validate_args(self, **kwargs) -> Optional[str]:
        """
        Validate tool arguments before execution.
        
        Override this method to add custom validation logic. Called by
        execute() before running the tool.
        
        Args:
            **kwargs: Arguments to validate
        
        Returns:
            Optional[str]: None if valid, error message string if invalid
        
        Default Behavior:
            Validates required parameters from get_schema() are present.
        
        Example:
            ```python
            def validate_args(self, **kwargs):
                # Call parent validation first
                error = super().validate_args(**kwargs)
                if error:
                    return error
                
                # Custom validation
                url = kwargs.get("url", "")
                if not url.startswith("http"):
                    return "URL must start with http:// or https://"
                
                return None  # Valid
            ```
        """
        schema = self.get_schema()
        
        # Check required parameters
        for param_name, param_config in schema.items():
            if param_config.get("required", False):
                if param_name not in kwargs or kwargs[param_name] is None:
                    return f"Missing required parameter: {param_name}"
        
        return None  # Valid
    
    # -------------------------------------------------------------------------
    # Utility methods - Use these in your tool implementations
    # -------------------------------------------------------------------------
    
    def get_default_args(self) -> Dict[str, Any]:
        """
        Get a dictionary of default argument values from the schema.
        
        Useful for merging with provided arguments to ensure all defaults
        are applied.
        
        Returns:
            Dict[str, Any]: Parameter name -> default value mapping
        
        Example:
            ```python
            defaults = self.get_default_args()
            # {'format': 'markdown', 'timeout': 30000}
            ```
        """
        schema = self.get_schema()
        defaults = {}
        
        for param_name, param_config in schema.items():
            if "default" in param_config:
                defaults[param_name] = param_config["default"]
        
        return defaults
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(name='{self.name}', type='{self.tool_type}')"
