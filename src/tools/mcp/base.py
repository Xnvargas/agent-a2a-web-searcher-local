"""
=============================================================================
MCP TOOL BASE CLASS - Base for All MCP-Based Tools
=============================================================================

This module provides the MCPTool abstract base class that all MCP-based tools
should extend. MCPTool handles the common functionality for communicating with
MCP servers via JSON-RPC.

WHAT TO IMPLEMENT:
------------------

When creating a new MCP tool, you need to:

1. Set class attributes:
   - name: Unique tool name (e.g., "firecrawl_scrape")
   - description: What the tool does
   - mcp_server_url: URL of the MCP server (can override via env var)

2. Implement required methods:
   - get_schema(): Define parameters
   - get_langchain_tool(): Return @tool decorated function

3. Optionally override:
   - execute(): If you need custom execution logic
   - get_citation_metadata(): For custom citation extraction


MINIMAL EXAMPLE:
----------------

```python
from tools.mcp.base import MCPTool
from langchain_core.tools import tool

class MyMCPTool(MCPTool):
    name = "my_mcp_tool"
    description = "Does something via MCP"
    mcp_server_url = "http://localhost:3000/mcp"
    
    def get_schema(self) -> dict:
        return {
            "param1": {"type": "string", "required": True, "description": "First param"}
        }
    
    def get_langchain_tool(self):
        @tool
        def my_mcp_tool(param1: str) -> str:
            '''Does something via MCP'''
            return "MCP_TOOL_PLACEHOLDER"
        return my_mcp_tool
```

The execute() method is inherited from MCPTool and handles MCP communication.


FULL EXAMPLE WITH CUSTOM CITATION:
----------------------------------

```python
from tools.mcp.base import MCPTool
from langchain_core.tools import tool
from datetime import datetime

class WebScrapeTool(MCPTool):
    name = "web_scrape"
    description = "Scrape content from a URL"
    mcp_server_url = os.getenv("SCRAPER_MCP_URL", "http://localhost:3000/mcp")
    
    def get_schema(self) -> dict:
        return {
            "url": {
                "type": "string", 
                "required": True, 
                "description": "URL to scrape"
            },
            "format": {
                "type": "string",
                "required": False,
                "default": "markdown",
                "description": "Output format"
            }
        }
    
    def get_langchain_tool(self):
        @tool
        def web_scrape(url: str, format: str = "markdown") -> str:
            '''Scrape content from a URL'''
            return "MCP_TOOL_PLACEHOLDER"
        return web_scrape
    
    def get_citation_metadata(self, tool_args, tool_result):
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "web_scrape",
            "url": tool_args.get("url", ""),
            "format": tool_args.get("format", "markdown"),
            "content_preview": str(tool_result)[:200]
        }
```

=============================================================================
"""

import os
import json
from abc import abstractmethod
from typing import Any, Dict, Callable
from datetime import datetime

from ..base import BaseTool
from .client import get_mcp_client, DEFAULT_MCP_TIMEOUT


class MCPTool(BaseTool):
    """
    Abstract base class for MCP-based tools.
    
    MCPTool extends BaseTool with MCP-specific functionality:
    - Automatic MCP server communication via MCPClient
    - Default execute() implementation that calls the MCP server
    - Response parsing for MCP content format
    
    Subclasses only need to implement:
    - get_schema(): Define the tool's parameters
    - get_langchain_tool(): Return @tool decorated function
    
    Optionally override:
    - execute(): For custom execution logic
    - get_citation_metadata(): For custom citation extraction
    - mcp_server_url: To change the MCP server
    
    Attributes:
        name (str): Unique tool name - MUST match function name in get_langchain_tool()
        description (str): Tool description shown to LLM
        mcp_server_url (str): URL of the MCP server for this tool
        mcp_timeout (float): Timeout for MCP requests in seconds
        tool_type (str): Always "mcp" for MCP tools
    
    Example:
        ```python
        class MyTool(MCPTool):
            name = "my_tool"
            description = "Does something"
            mcp_server_url = "http://localhost:3000/mcp"
            
            def get_schema(self) -> dict:
                return {"param": {"type": "string", "required": True}}
            
            def get_langchain_tool(self):
                @tool
                def my_tool(param: str) -> str:
                    '''Does something'''
                    return "PLACEHOLDER"
                return my_tool
        ```
    """
    
    # -------------------------------------------------------------------------
    # CLASS ATTRIBUTES - Override these in your tool subclass
    # -------------------------------------------------------------------------
    
    tool_type: str = "mcp"
    """Identifies this as an MCP tool. Do not change."""
    
    mcp_server_url: str = ""
    """
    URL of the MCP server for this tool.
    
    IMPORTANT: Set this in your tool subclass or it will fail.
    
    Best Practice: Use environment variable with fallback:
        mcp_server_url = os.getenv("MY_SERVICE_MCP_URL", "http://localhost:3000/mcp")
    
    Example:
        class FirecrawlScrapeTool(MCPTool):
            mcp_server_url = os.getenv("FIRECRAWL_MCP_URL", "http://192.168.0.229:3123/mcp")
    """
    
    mcp_timeout: float = DEFAULT_MCP_TIMEOUT
    """
    Timeout for MCP requests in seconds.
    Default is 120s to handle slow web scraping operations.
    Override if your tool needs different timeout.
    """
    
    # -------------------------------------------------------------------------
    # REQUIRED ABSTRACT METHODS - You MUST implement these
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the parameter schema for this tool.
        
        See BaseTool.get_schema() for full documentation.
        
        Returns:
            Dict mapping parameter names to their configs:
            - type: "string", "integer", "boolean", "array", "object"
            - required: True/False
            - description: What the parameter does
            - default: Optional default value
        
        Example:
            ```python
            def get_schema(self) -> dict:
                return {
                    "url": {
                        "type": "string",
                        "required": True,
                        "description": "URL to scrape"
                    },
                    "format": {
                        "type": "string",
                        "required": False,
                        "default": "markdown"
                    }
                }
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
                def firecrawl_scrape(url: str, format: str = "markdown") -> str:
                    '''Scrape content from a URL and return as markdown.'''
                    return "MCP_TOOL_PLACEHOLDER"
                return firecrawl_scrape
            ```
        
        Important Notes:
            - Function name must match self.name
            - Docstring becomes the tool description in LangChain
            - Parameter types affect JSON schema generation
            - Default values should match get_schema() defaults
        """
        pass
    
    # -------------------------------------------------------------------------
    # EXECUTION - Override if you need custom logic
    # -------------------------------------------------------------------------
    
    async def execute(self, **kwargs) -> str:
        """
        Execute the tool via MCP server.
        
        Default implementation:
        1. Gets or creates MCP client for mcp_server_url
        2. Calls the tool on the MCP server with kwargs
        3. Parses the MCP response format
        4. Returns the content as a string
        
        Override this method only if you need custom execution logic,
        such as pre-processing arguments or post-processing results.
        
        Args:
            **kwargs: Tool arguments matching get_schema()
        
        Returns:
            str: Tool result as a string (content extracted from MCP response)
        
        Error Handling:
            Returns error messages as strings, not exceptions.
            The LLM will see the error and can decide how to proceed.
        
        Example Override:
            ```python
            async def execute(self, url: str, **kwargs) -> str:
                # Pre-process: ensure URL has protocol
                if not url.startswith("http"):
                    url = "https://" + url
                
                # Call parent execute
                result = await super().execute(url=url, **kwargs)
                
                # Post-process: truncate if too long
                if len(result) > 10000:
                    result = result[:10000] + "\\n... (truncated)"
                
                return result
            ```
        """
        print(f"\n{'#'*80}")
        print(f"# MCP TOOL EXECUTE: {self.name}")
        print(f"# Server: {self.mcp_server_url}")
        print(f"# Arguments: {json.dumps(kwargs, indent=2)}")
        print(f"{'#'*80}")
        
        # Validate we have a server URL
        if not self.mcp_server_url:
            error_msg = f"MCP Error: No mcp_server_url configured for tool '{self.name}'"
            print(f"\n❌ {error_msg}")
            return error_msg
        
        try:
            # Get or create MCP client
            client = await get_mcp_client(self.mcp_server_url, self.mcp_timeout)
            
            # Call the tool on the MCP server
            result = await client.call_tool(self.name, kwargs)
            
            # Extract content from MCP response format
            return self._parse_mcp_response(result)
            
        except Exception as e:
            error_msg = f"MCP Execution Error ({self.name}): {type(e).__name__}: {str(e)}"
            print(f"\n❌ {error_msg}")
            return error_msg
    
    def _parse_mcp_response(self, result: Dict[str, Any]) -> str:
        """
        Parse MCP JSON-RPC response and extract content.
        
        MCP responses typically have this structure:
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {"type": "text", "text": "actual content here"}
                ]
            }
        }
        
        This method extracts the text content and returns it as a string.
        
        Args:
            result: Raw MCP JSON-RPC response
        
        Returns:
            str: Extracted content or error message
        """
        # Check for error
        if "error" in result:
            error_msg = f"MCP Error: {result['error']}"
            print(f"\n❌ {error_msg}")
            return error_msg
        
        # Parse MCP response format
        if "result" in result:
            mcp_result = result["result"]
            
            # Handle content array format (standard MCP format)
            if isinstance(mcp_result, dict) and "content" in mcp_result:
                content_items = mcp_result.get("content", [])
                extracted_parts = []
                
                for item in content_items:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            extracted_parts.append(item.get("text", ""))
                        elif "text" in item:
                            extracted_parts.append(item["text"])
                
                if extracted_parts:
                    final_content = "\n".join(extracted_parts)
                    print(f"\n✅ Successfully extracted {len(final_content)} characters of content")
                    return final_content
            
            # Direct string result
            if isinstance(mcp_result, str):
                return mcp_result
            
            # Fallback: return as JSON
            return json.dumps(mcp_result, indent=2)
        
        # Fallback: return full response as JSON
        return json.dumps(result, indent=2)
    
    # -------------------------------------------------------------------------
    # CITATION - Override for custom citation extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """
        Extract citation metadata from MCP tool execution.
        
        Default implementation provides basic metadata. Override this for
        tool-specific citation extraction (e.g., extracting URL from scrape).
        
        Args:
            tool_args: Arguments passed to the tool
            tool_result: Result from execute()
        
        Returns:
            Citation metadata dictionary
        
        Override Example (for a web scraping tool):
            ```python
            def get_citation_metadata(self, tool_args, tool_result):
                # Get actual URL (may differ from input due to redirects)
                actual_url = tool_args.get("url", "")
                if isinstance(tool_result, dict):
                    actual_url = tool_result.get("metadata", {}).get("sourceURL", actual_url)
                
                return {
                    "tool": self.name,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source_type": "web_scrape",
                    "url": actual_url,
                    "content_format": tool_args.get("formats", ["markdown"])[0],
                    "content_preview": str(tool_result)[:200]
                }
            ```
        """
        citation = {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "mcp",
            "mcp_server": self.mcp_server_url,
        }
        
        # Try to extract URL if present in args
        if "url" in tool_args:
            citation["url"] = tool_args["url"]
        elif "urls" in tool_args:
            citation["urls"] = tool_args["urls"]
        
        # Extract content preview
        if isinstance(tool_result, str):
            preview = tool_result[:200]
            if len(tool_result) > 200:
                preview += "..."
            citation["content_preview"] = preview
        
        return citation
