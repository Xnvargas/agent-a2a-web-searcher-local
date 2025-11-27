"""
=============================================================================
MCP CLIENT - HTTP Client for Model Context Protocol Communication
=============================================================================

This module provides the MCPClient class for communicating with MCP servers
using the Streamable HTTP transport. It handles:

- JSON-RPC protocol formatting
- SSE (Server-Sent Events) response parsing
- Session initialization
- Tool discovery and execution

USAGE:
------

The MCPClient is typically not used directly. Instead, MCPTool subclasses
use it internally to execute their tools. However, you can use it directly
for testing:

```python
from tools.mcp.client import MCPClient

async def test_mcp():
    client = MCPClient("http://localhost:3000/mcp")
    await client.initialize()
    
    # List available tools
    tools = await client.list_tools()
    
    # Execute a tool
    result = await client.call_tool("firecrawl_scrape", {"url": "https://example.com"})
```

CONFIGURATION:
--------------

MCP server URLs are configured per-tool (or per-service) via class attributes
or environment variables. See MCPTool base class for details.

=============================================================================
"""

import os
import json
import httpx
from typing import Any, Dict, Optional


# =============================================================================
# DEFAULT CONFIGURATION
# These can be overridden via environment variables
# =============================================================================

DEFAULT_MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT", "120.0"))
"""
Default timeout for MCP requests in seconds.
Override with MCP_TIMEOUT environment variable.
Web scraping operations can take 30-60+ seconds, so default is high.
"""


class MCPClient:
    """
    HTTP Client for communicating with MCP servers using Streamable HTTP transport.
    
    This client implements the MCP JSON-RPC protocol for tool execution. It handles:
    
    - Connection initialization and capability negotiation
    - JSON-RPC request/response formatting
    - SSE (Server-Sent Events) response parsing
    - Error handling and retries
    
    Attributes:
        server_url (str): Full URL to the MCP server endpoint
        timeout (float): Request timeout in seconds
        
    Protocol Details:
        - Uses JSON-RPC 2.0 over HTTP POST
        - Server may respond with JSON or SSE (text/event-stream)
        - Initialization handshake required before tool calls
    
    Example:
        ```python
        client = MCPClient("http://localhost:3000/mcp", timeout=60.0)
        await client.initialize()
        result = await client.call_tool("my_tool", {"arg1": "value1"})
        ```
    
    Thread Safety:
        The client is NOT thread-safe. Create one client per async context.
    """
    
    def __init__(self, server_url: str, timeout: float = DEFAULT_MCP_TIMEOUT):
        """
        Initialize MCP client.
        
        Args:
            server_url: Full URL to the MCP server endpoint.
                       Example: "http://192.168.0.229:3123/mcp"
                       Include the /mcp path if your server requires it.
            
            timeout: Request timeout in seconds. Default 120s is high because
                    web scraping operations can take 30-60+ seconds.
        
        Note:
            Call initialize() before using call_tool().
        """
        self.server_url = server_url
        self.timeout = timeout
        self._session_id: Optional[str] = None
        self._request_id: int = 0
        self._initialized: bool = False
    
    # -------------------------------------------------------------------------
    # Internal helper methods
    # -------------------------------------------------------------------------
    
    def _next_request_id(self) -> int:
        """
        Generate next JSON-RPC request ID.
        
        JSON-RPC requires unique IDs for request/response matching.
        We use a simple incrementing integer.
        """
        self._request_id += 1
        return self._request_id
    
    def _parse_sse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse SSE (Server-Sent Events) response from MCP server.
        
        MCP servers may return responses as SSE streams. This method extracts
        the final data event from the stream.
        
        SSE Format:
            event: message
            data: {"jsonrpc": "2.0", "id": 1, "result": {...}}
        
        Args:
            response_text: Raw SSE response text
        
        Returns:
            Parsed JSON-RPC response dictionary
        """
        print(f"\n🔍 Parsing SSE response...")
        print(f"🔍 Raw response length: {len(response_text)} chars")
        
        # SSE format: "event: message\ndata: {...json...}\n\n"
        last_data = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('data:'):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        last_data = json.loads(data_str)
                        print(f"🔍 Parsed SSE data event")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ SSE data parse error: {e}")
                        continue
        
        if last_data:
            return last_data
        
        # Try parsing as regular JSON if SSE parsing fails
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"error": f"Could not parse response: {response_text[:500]}"}
    
    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an HTTP request to the MCP server and handle response.
        
        Handles both JSON and SSE response formats. Includes detailed logging
        for debugging MCP communication issues.
        
        Args:
            payload: JSON-RPC request payload
        
        Returns:
            Parsed JSON-RPC response
        
        Error Handling:
            - Timeout: Returns {"error": "Request timeout after Xs"}
            - Connection: Returns {"error": "Connection error to URL: details"}
            - Protocol: Returns {"error": "Remote protocol error: details"}
            - Other: Returns {"error": "ExceptionType: details"}
        """
        print(f"\n📤 Sending MCP Request:\n{json.dumps(payload, indent=2)}")
        print(f"📤 Target: {self.server_url}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                )
                
                print(f"\n📥 Response Status: {response.status_code}")
                print(f"📥 Response Headers: {dict(response.headers)}")
                
                content_type = response.headers.get("content-type", "")
                response_text = response.text
                
                print(f"📥 Content-Type: {content_type}")
                print(f"📥 Response Body (first 2000 chars):\n{response_text[:2000]}")
                if len(response_text) > 2000:
                    print(f"... (truncated, total: {len(response_text)} chars)")
                
                if response.status_code == 200:
                    # Check if response is SSE
                    if "text/event-stream" in content_type:
                        return self._parse_sse_response(response_text)
                    else:
                        try:
                            return response.json()
                        except json.JSONDecodeError:
                            # Try SSE parsing as fallback
                            return self._parse_sse_response(response_text)
                else:
                    return {"error": f"HTTP {response.status_code}: {response_text}"}
                    
        except httpx.TimeoutException:
            error_msg = f"Request timeout after {self.timeout}s"
            print(f"❌ Timeout Error: {error_msg}")
            return {"error": error_msg}
        except httpx.ConnectError as e:
            error_msg = f"Connection error to {self.server_url}: {str(e)}"
            print(f"❌ Connection Error: {error_msg}")
            return {"error": error_msg}
        except httpx.RemoteProtocolError as e:
            error_msg = f"Remote protocol error: {str(e)}"
            print(f"❌ Protocol Error: {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"❌ Unexpected Error: {error_msg}")
            return {"error": error_msg}
    
    # -------------------------------------------------------------------------
    # Public API methods
    # -------------------------------------------------------------------------
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize MCP session with the server.
        
        This MUST be called before using call_tool(). It sends the 'initialize'
        JSON-RPC request to establish protocol version and capabilities.
        
        Returns:
            Server capabilities and protocol info dictionary
        
        Protocol:
            1. Send 'initialize' with client info and capabilities
            2. Server responds with its capabilities
            3. Send 'notifications/initialized' to confirm
        
        Example:
            ```python
            client = MCPClient("http://localhost:3000/mcp")
            init_result = await client.initialize()
            print(f"Server capabilities: {init_result}")
            ```
        """
        print(f"\n{'='*80}")
        print(f"🔌 MCP CLIENT: Initializing connection to {self.server_url}")
        print(f"{'='*80}")
        
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "langgraph-agent",
                    "version": "1.0.0"
                }
            }
        }
        
        result = await self._make_request(request_payload)
        
        if "error" not in result:
            self._initialized = True
            print(f"✅ Initialization successful!")
            # Send initialized notification
            await self._send_initialized_notification()
        else:
            print(f"❌ Initialization failed: {result.get('error')}")
        
        return result
    
    async def _send_initialized_notification(self) -> None:
        """
        Send the 'initialized' notification after successful initialization.
        
        This is part of the MCP protocol handshake. The notification tells
        the server that the client is ready to make requests.
        """
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        print(f"\n📤 Sending initialized notification...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.server_url,
                    json=notification,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                )
                print(f"📥 Initialized notification response: {response.status_code}")
        except Exception as e:
            # Non-fatal - some servers don't require this notification
            print(f"⚠️ Initialized notification error (non-fatal): {e}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        List available tools from the MCP server.
        
        Returns:
            Dictionary with 'result' containing 'tools' array, or 'error'.
        
        Example Response:
            ```json
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {
                            "name": "firecrawl_scrape",
                            "description": "Scrape content from URL",
                            "inputSchema": {...}
                        }
                    ]
                }
            }
            ```
        """
        print(f"\n{'='*80}")
        print(f"🔧 MCP CLIENT: Listing available tools")
        print(f"{'='*80}")
        
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/list",
            "params": {}
        }
        
        result = await self._make_request(request_payload)
        
        if "result" in result and "tools" in result.get("result", {}):
            tools = result["result"]["tools"]
            print(f"\n✅ Found {len(tools)} tools")
        
        return result
    
    async def call_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to execute (e.g., 'firecrawl_scrape')
            tool_args: Arguments to pass to the tool (matches tool's inputSchema)
        
        Returns:
            Tool execution result dictionary, or error dictionary
        
        Example:
            ```python
            result = await client.call_tool(
                "firecrawl_scrape",
                {"url": "https://example.com", "formats": ["markdown"]}
            )
            ```
        
        Response Format:
            Success:
            ```json
            {
                "jsonrpc": "2.0",
                "id": 3,
                "result": {
                    "content": [{"type": "text", "text": "scraped content..."}]
                }
            }
            ```
            
            Error:
            ```json
            {"error": "Error description"}
            ```
        """
        print(f"\n{'='*80}")
        print(f"🔧 MCP CLIENT: Calling tool '{tool_name}'")
        print(f"{'='*80}")
        print(f"📤 Tool Arguments:\n{json.dumps(tool_args, indent=2)}")
        
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_args
            }
        }
        
        result = await self._make_request(request_payload)
        
        # Extract and preview content if successful
        if "result" in result:
            content = result["result"]
            if isinstance(content, dict) and "content" in content:
                content_items = content.get("content", [])
                if content_items and isinstance(content_items, list):
                    extracted_text = ""
                    for item in content_items:
                        if isinstance(item, dict) and item.get("type") == "text":
                            extracted_text += item.get("text", "")
                    if extracted_text:
                        print(f"\n📄 Extracted Content Preview (first 1000 chars):\n{extracted_text[:1000]}")
                        if len(extracted_text) > 1000:
                            print(f"... (truncated, total: {len(extracted_text)} chars)")
            print(f"\n✅ Tool '{tool_name}' completed successfully")
        else:
            print(f"\n❌ Tool '{tool_name}' failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    @property
    def is_initialized(self) -> bool:
        """Check if the client has been initialized."""
        return self._initialized


# =============================================================================
# Global MCP Client Management
# =============================================================================

# Cache of MCP clients by server URL
_mcp_clients: Dict[str, MCPClient] = {}


async def get_mcp_client(server_url: str, timeout: float = DEFAULT_MCP_TIMEOUT) -> MCPClient:
    """
    Get or create an MCP client for the given server URL.
    
    This function manages a cache of MCP clients. If a client for the URL
    already exists and is initialized, it returns the existing client.
    Otherwise, it creates and initializes a new one.
    
    Args:
        server_url: MCP server URL (e.g., "http://localhost:3000/mcp")
        timeout: Optional timeout override
    
    Returns:
        Initialized MCPClient instance
    
    Example:
        ```python
        client = await get_mcp_client("http://localhost:3000/mcp")
        result = await client.call_tool("my_tool", {"arg": "value"})
        ```
    
    Caching:
        Clients are cached by URL. Multiple calls with the same URL return
        the same client instance. This avoids repeated initialization.
    """
    global _mcp_clients
    
    if server_url not in _mcp_clients:
        client = MCPClient(server_url, timeout)
        await client.initialize()
        # Optionally list tools to verify connection
        await client.list_tools()
        _mcp_clients[server_url] = client
    
    return _mcp_clients[server_url]


def clear_mcp_clients() -> None:
    """
    Clear all cached MCP clients.
    
    Useful for testing or when you need to reset connections.
    """
    global _mcp_clients
    _mcp_clients.clear()
    print("✓ Cleared all cached MCP clients")
