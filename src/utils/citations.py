"""
=============================================================================
CITATION UTILITIES - Helpers for Formatting Tool Citations
=============================================================================

This module provides utilities for formatting tool execution results and
citations for display in the BeeAI UI and terminal logging.

USAGE:
------

These utilities are used internally by the agent to format tool results
for display. You can also use them for custom logging:

```python
from utils.citations import format_tool_data_for_logging, print_tool_execution

# Log tool execution to terminal
print_tool_execution(
    tool_name="firecrawl_scrape",
    tool_args={"url": "https://example.com"},
    tool_result="Scraped content here..."
)

# Format for trajectory logging
formatted = format_tool_data_for_logging(
    tool_name="firecrawl_scrape",
    tool_args={"url": "https://example.com"},
    tool_result="Scraped content here..."
)
```

=============================================================================
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json


def format_citation(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any,
    timestamp: str = None
) -> Dict[str, Any]:
    """
    Format a citation dictionary from tool execution data.
    
    Creates a standardized citation format that can be used for:
    - BeeAI citation extension
    - Trajectory logging
    - Source attribution
    
    Args:
        tool_name: Name of the tool that was executed
        tool_args: Arguments passed to the tool
        tool_result: Result returned by the tool
        timestamp: ISO format timestamp (auto-generated if not provided)
    
    Returns:
        Citation dictionary with standardized fields
    
    Example:
        ```python
        citation = format_citation(
            tool_name="firecrawl_scrape",
            tool_args={"url": "https://example.com"},
            tool_result="Page content...",
        )
        # Returns:
        # {
        #     "tool": "firecrawl_scrape",
        #     "timestamp": "2024-01-01T12:00:00Z",
        #     "url": "https://example.com",
        #     "content_preview": "Page content..."
        # }
        ```
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    
    citation = {
        "tool": tool_name,
        "timestamp": timestamp,
    }
    
    # Extract URL if present
    if "url" in tool_args:
        citation["url"] = tool_args["url"]
    elif "urls" in tool_args:
        citation["urls"] = tool_args["urls"]
    
    # Extract query if present (for search tools)
    if "query" in tool_args:
        citation["search_query"] = tool_args["query"]
    
    # Add content preview
    if isinstance(tool_result, str):
        preview = tool_result[:200]
        if len(tool_result) > 200:
            preview += "..."
        citation["content_preview"] = preview
    
    return citation


def format_citations_for_beeai(
    citations: List[Dict[str, Any]],
    final_response: str
) -> List[Dict[str, Any]]:
    """
    Format citations for the BeeAI citation extension.
    
    Converts internal citation format to BeeAI's expected format with
    position markers in the response text.
    
    Args:
        citations: List of citation dictionaries from tool execution
        final_response: The final response text to anchor citations to
    
    Returns:
        List of formatted citations for BeeAI
    
    BeeAI Citation Format:
        {
            "url": "https://example.com",
            "title": "Source 1: firecrawl_scrape",
            "description": "Format: markdown | Scraped: 2024-01-01T12:00:00Z",
            "start_index": 0,
            "end_index": 100
        }
    """
    formatted_citations = []
    
    for idx, cite in enumerate(citations, 1):
        # Build citation title
        citation_title = f"Source {idx}: {cite.get('tool', 'unknown')}"
        
        # Build citation description
        description_parts = []
        
        if 'content_format' in cite:
            description_parts.append(f"Format: {cite['content_format']}")
        if 'search_query' in cite:
            description_parts.append(f"Query: {cite['search_query']}")
        if 'timestamp' in cite:
            description_parts.append(f"Retrieved: {cite['timestamp']}")
        
        citation_description = " | ".join(description_parts) if description_parts else "Tool execution"
        
        # Get URL from citation
        citation_url = cite.get('url', cite.get('base_url', ''))
        if isinstance(citation_url, list) and citation_url:
            citation_url = citation_url[0]  # Use first URL if list
        
        formatted_citations.append({
            "url": citation_url or "",
            "title": citation_title,
            "description": citation_description,
            "start_index": 0,  # Citations cover entire response by default
            "end_index": len(final_response)
        })
    
    return formatted_citations


def format_tool_data_for_logging(
    tool_name: str, 
    tool_args: Dict[str, Any], 
    tool_result: Any = None, 
    error: str = None
) -> Dict[str, str]:
    """
    Format tool execution data for consistent logging.
    
    Creates formatted strings for both terminal output and trajectory
    logging in the BeeAI UI.
    
    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to the tool
        tool_result: Result returned by the tool (optional)
        error: Error message if execution failed (optional)
    
    Returns:
        Dictionary with formatted strings:
        - terminal_invocation: Header for terminal output
        - terminal_args: Arguments formatted for terminal
        - terminal_result: Result formatted for terminal
        - terminal_error: Error formatted for terminal
        - trajectory_args: Arguments for trajectory logging
        - trajectory_result: Result for trajectory logging
        - trajectory_error: Error for trajectory logging
    
    Example:
        ```python
        formatted = format_tool_data_for_logging(
            tool_name="firecrawl_scrape",
            tool_args={"url": "https://example.com"},
            tool_result="Page content..."
        )
        print(formatted["terminal_invocation"])
        print(formatted["terminal_args"])
        ```
    """
    formatted = {
        "header": "=" * 80,
        "terminal_invocation": f"\n{'=' * 80}\n🔧 MCP TOOL INVOCATION: {tool_name}\n{'=' * 80}",
        "terminal_args": f"📥 Arguments:\n{json.dumps(tool_args, indent=2)}",
        "terminal_result": "",
        "terminal_error": "",
        "trajectory_args": json.dumps(tool_args, indent=2),
        "trajectory_result": "",
        "trajectory_error": ""
    }
    
    if tool_result is not None:
        # Format result based on type
        if isinstance(tool_result, (dict, list)):
            result_str = json.dumps(tool_result, indent=2)
        else:
            result_str = str(tool_result)
        
        formatted["terminal_result"] = f"✅ Result:\n{result_str}\n{'=' * 80}\n"
        formatted["trajectory_result"] = result_str
    
    if error:
        formatted["terminal_error"] = f"❌ Error:\n{error}\n{'=' * 80}\n"
        formatted["trajectory_error"] = error
    
    return formatted


def print_tool_execution(
    tool_name: str, 
    tool_args: Dict[str, Any], 
    tool_result: Any = None, 
    error: str = None
) -> None:
    """
    Print tool execution information to terminal with structured formatting.
    
    Convenience function that formats and prints tool execution data.
    
    Args:
        tool_name: Name of the tool
        tool_args: Arguments passed to the tool
        tool_result: Result returned by the tool (optional)
        error: Error message if execution failed (optional)
    
    Example:
        ```python
        print_tool_execution(
            tool_name="searx_search",
            tool_args={"query": "python tutorials"},
            tool_result="Found 5 results..."
        )
        ```
    """
    formatted = format_tool_data_for_logging(tool_name, tool_args, tool_result, error)
    
    print(formatted["terminal_invocation"])
    print(formatted["terminal_args"])
    
    if tool_result is not None:
        print(formatted["terminal_result"])
    
    if error:
        print(formatted["terminal_error"])
