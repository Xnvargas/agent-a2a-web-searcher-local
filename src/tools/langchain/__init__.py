"""
=============================================================================
LANGCHAIN TOOLS PACKAGE - Native Python-Based Tools
=============================================================================

This package contains tools that execute locally via Python, using LangChain's
tool infrastructure. Unlike MCP tools, these don't require external servers.

WHAT ARE LANGCHAIN TOOLS?
-------------------------

LangChain tools are Python functions decorated with @tool that:
- Execute locally in the agent process
- Can use any Python library (API clients, databases, etc.)
- Are simpler to implement than MCP tools
- Don't require a separate server

Use LangChain tools when:
- You want to wrap an existing Python library
- You need simple, synchronous operations
- You don't need the MCP protocol overhead

LANGCHAIN TOOL ARCHITECTURE:
----------------------------

    tools/langchain/
    ├── __init__.py      # This file - package exports
    ├── base.py          # LangChainTool base class (extend this)
    └── searx/           # Example: SearxNG search tools
        ├── __init__.py
        └── search.py


HOW TO ADD A NEW LANGCHAIN SERVICE:
-----------------------------------

1. Create a directory for your service: tools/langchain/your_service/
2. Create tool files extending LangChainTool
3. Create __init__.py to register your tools
4. Import in tools/langchain/__init__.py

Example - Adding a Weather API tool:

1. Create tools/langchain/weather/get_weather.py:
   ```python
   import os
   from tools.langchain.base import LangChainTool
   from langchain_core.tools import tool
   import httpx
   
   class GetWeatherTool(LangChainTool):
       name = "get_weather"
       description = "Get current weather for a city"
       
       def get_schema(self) -> dict:
           return {
               "city": {"type": "string", "required": True}
           }
       
       async def execute(self, city: str) -> str:
           api_key = os.getenv("WEATHER_API_KEY")
           async with httpx.AsyncClient() as client:
               response = await client.get(f"https://api.weather.com/{city}?key={api_key}")
               return response.json()
       
       def get_langchain_tool(self):
           @tool
           def get_weather(city: str) -> str:
               '''Get current weather for a city'''
               return "LANGCHAIN_TOOL_PLACEHOLDER"
           return get_weather
   ```

2. Create tools/langchain/weather/__init__.py:
   ```python
   from tools.registry import ToolRegistry
   from .get_weather import GetWeatherTool
   
   ToolRegistry.register(GetWeatherTool())
   ```

3. Add to tools/langchain/__init__.py:
   ```python
   from . import weather  # Triggers registration
   ```

=============================================================================
"""

# -----------------------------------------------------------------------------
# LangChain Infrastructure
# -----------------------------------------------------------------------------
from .base import LangChainTool

# -----------------------------------------------------------------------------
# Import LangChain service packages to trigger tool registration
# Add new services here
# -----------------------------------------------------------------------------

# SearxNG - Privacy-respecting metasearch
from . import searx

# -----------------------------------------------------------------------------
# ADD NEW LANGCHAIN SERVICES HERE:
# Example:
# from . import weather     # Weather API tools
# from . import calculator  # Math calculation tools
# from . import database    # Database query tools
# -----------------------------------------------------------------------------

__all__ = [
    "LangChainTool",
]
