"""
=============================================================================
FIRECRAWL EXTRACT TOOL - Extract Structured Data from Web Pages
=============================================================================

This tool uses LLM capabilities to extract structured information from
web pages based on a custom prompt and optional schema.

WHEN TO USE:
- You need to extract specific data points from pages (prices, names, etc.)
- You want structured JSON output from unstructured web content
- You need to extract information following a specific schema

USE FIRECRAWL_SCRAPE INSTEAD WHEN:
- You just need the raw content
- You don't need structured extraction
- You want to process the content yourself

=============================================================================
"""

from typing import Any, Dict, List
from datetime import datetime
from langchain_core.tools import tool

from tools.mcp.base import MCPTool
from . import FIRECRAWL_MCP_URL


class FirecrawlExtractTool(MCPTool):
    """
    Tool for extracting structured data from web pages using Firecrawl MCP.
    
    This tool uses LLM capabilities to extract specific information from
    web pages based on a custom prompt. You can optionally provide a JSON
    schema to ensure consistent structured output.
    
    Features:
        - LLM-powered extraction
        - Custom extraction prompts
        - Optional JSON schema for structured output
        - Can extract from multiple URLs at once
    
    Example Usage:
        ```python
        tool = FirecrawlExtractTool()
        result = await tool.execute(
            urls=["https://example.com/product"],
            prompt="Extract the product name, price, and description",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                    "description": {"type": "string"}
                }
            }
        )
        ```
    """
    
    # -------------------------------------------------------------------------
    # Tool Configuration
    # -------------------------------------------------------------------------
    
    name = "firecrawl_extract"
    description = "Extract structured information from web pages using LLM capabilities."
    mcp_server_url = FIRECRAWL_MCP_URL
    
    # -------------------------------------------------------------------------
    # Schema Definition
    # -------------------------------------------------------------------------
    
    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        """Define the parameters for the extract tool."""
        return {
            "urls": {
                "type": "array",
                "required": True,
                "description": "Array of URLs to extract information from."
            },
            "prompt": {
                "type": "string",
                "required": True,
                "description": "Custom prompt describing what information to extract. Be specific about the data points you want."
            },
            "extraction_schema": {
                "type": "object",
                "required": False,
                "description": "Optional JSON schema for structured data extraction. Ensures consistent output format."
            }
        }
    
    # -------------------------------------------------------------------------
    # LangChain Tool Definition
    # -------------------------------------------------------------------------
    
    def get_langchain_tool(self):
        """Return the LangChain @tool decorated function."""
        @tool
        def firecrawl_extract(
            urls: List[str],
            prompt: str,
            extraction_schema: dict = None
        ) -> str:
            """
            Extract structured information from web pages using LLM.
            
            Use this tool when you need to extract specific data points from
            web pages in a structured format. The LLM will analyze the page
            content and extract information based on your prompt.
            
            Args:
                urls: Array of URLs to extract information from
                prompt: Description of what information to extract
                extraction_schema: Optional JSON schema for structured output
            
            Returns:
                Extracted structured data as JSON
            """
            return "MCP_TOOL_PLACEHOLDER"
        
        return firecrawl_extract
    
    # -------------------------------------------------------------------------
    # Custom Citation Extraction
    # -------------------------------------------------------------------------
    
    def get_citation_metadata(
        self, 
        tool_args: Dict[str, Any], 
        tool_result: Any
    ) -> Dict[str, Any]:
        """Extract citation metadata from extraction results."""
        urls = tool_args.get("urls", [])
        return {
            "tool": self.name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_type": "structured_extraction",
            "urls": urls,
            "url_count": len(urls),
            "extraction_prompt": tool_args.get("prompt", "")[:100] + "..." if len(tool_args.get("prompt", "")) > 100 else tool_args.get("prompt", ""),
            "has_schema": tool_args.get("extraction_schema") is not None,
        }
