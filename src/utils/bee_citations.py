"""
=============================================================================
BEEAI CITATIONS - Citation Utilities for BeeAI Framework Agent
=============================================================================

This module provides citation formatting utilities specifically for the
BeeAI Framework agent. It mirrors the functionality of citations.py but
is optimized for BeeAI's execution model.

USAGE:
------

```python
from utils.bee_citations import format_bee_citations_for_beeai

# Format tool citations for the BeeAI UI
formatted = format_bee_citations_for_beeai(tool_citations, response_text)
```

=============================================================================
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


def format_bee_citation(citation_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a single citation metadata dict into BeeAI-compatible citation format.
    
    Args:
        citation_metadata: Dict from tool's get_citation_metadata() method
            Expected keys:
            - tool (str): Tool name
            - timestamp (str): ISO timestamp
            - source_type (str): Type of source
            - url (str, optional): Source URL
            - content_preview (str, optional): Content preview
    
    Returns:
        Dict formatted for BeeAI citation system
    
    Example:
        ```python
        metadata = {
            "tool": "searx_search",
            "timestamp": "2024-01-15T10:30:00Z",
            "source_type": "web_search",
            "query": "python tutorials"
        }
        formatted = format_bee_citation(metadata)
        # Returns: {"tool": "searx_search", "source": "web_search", ...}
        ```
    """
    citation = {
        "tool": citation_metadata.get("tool", "unknown"),
        "source": citation_metadata.get("source_type", "unknown"),
        "timestamp": citation_metadata.get("timestamp", datetime.utcnow().isoformat() + "Z"),
    }
    
    # Add URL if present
    if "url" in citation_metadata:
        citation["url"] = citation_metadata["url"]
    
    # Add URLs list if present (for batch operations)
    if "urls" in citation_metadata:
        citation["urls"] = citation_metadata["urls"]
    
    # Add query if present (for search tools)
    if "query" in citation_metadata:
        citation["query"] = citation_metadata["query"]
    
    # Add content preview if present
    if "content_preview" in citation_metadata:
        citation["preview"] = citation_metadata["content_preview"]
    
    # Add any MCP-specific metadata
    if "mcp_server" in citation_metadata:
        citation["mcp_server"] = citation_metadata["mcp_server"]
    
    return citation


def format_bee_citations_for_beeai(
    citations: List[Dict[str, Any]], 
    response_text: str
) -> List[Dict[str, Any]]:
    """
    Format a list of citation metadata into BeeAI UI-compatible citations.
    
    This function processes citations from BeeAI agent tool executions and
    formats them for the BeeAI citation extension.
    
    Args:
        citations: List of citation metadata dicts from tool executions
        response_text: The final response text (used for context)
    
    Returns:
        List of formatted citations for BeeAI citation extension
    
    Example:
        ```python
        tool_citations = [
            {"tool": "searx_search", "source_type": "web_search", ...},
            {"tool": "firecrawl_scrape", "source_type": "web_scrape", ...}
        ]
        
        formatted = format_bee_citations_for_beeai(tool_citations, response)
        # Use with citation.message(text=response, citations=formatted)
        ```
    """
    if not citations:
        return []
    
    formatted_citations = []
    
    for idx, citation_metadata in enumerate(citations):
        try:
            formatted = format_bee_citation(citation_metadata)
            formatted["index"] = idx
            formatted_citations.append(formatted)
        except Exception as e:
            print(f"⚠️ BeeAI Citations: Failed to format citation {idx}: {e}")
            continue
    
    return formatted_citations


def format_bee_tool_data_for_logging(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any,
    execution_time_ms: Optional[float] = None
) -> str:
    """
    Format tool execution data for logging/trajectory display.
    
    Creates a formatted string representation of a tool execution
    suitable for logging or displaying in trajectory metadata.
    
    Args:
        tool_name: Name of the executed tool
        tool_args: Arguments passed to the tool
        tool_result: Result from the tool execution
        execution_time_ms: Optional execution time in milliseconds
    
    Returns:
        Formatted string for logging
    
    Example:
        ```python
        log_str = format_bee_tool_data_for_logging(
            tool_name="searx_search",
            tool_args={"query": "python"},
            tool_result="Found 5 results...",
            execution_time_ms=1234.5
        )
        print(log_str)
        ```
    """
    lines = [
        f"🐝 Tool: {tool_name}",
        f"📥 Arguments:",
        f"   {json.dumps(tool_args, indent=3)}",
    ]
    
    if execution_time_ms is not None:
        lines.append(f"⏱️ Execution Time: {execution_time_ms:.2f}ms")
    
    # Truncate result for logging
    result_str = str(tool_result)
    if len(result_str) > 500:
        result_str = result_str[:500] + "... (truncated)"
    
    lines.extend([
        f"📤 Result Preview:",
        f"   {result_str}"
    ])
    
    return "\n".join(lines)


def print_bee_tool_execution(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any,
    execution_time_ms: Optional[float] = None
) -> None:
    """
    Print formatted tool execution data to console.
    
    Convenience function for debugging BeeAI agent tool executions.
    
    Args:
        tool_name: Name of the executed tool
        tool_args: Arguments passed to the tool
        tool_result: Result from the tool execution
        execution_time_ms: Optional execution time in milliseconds
    """
    print("\n" + "=" * 60)
    print(format_bee_tool_data_for_logging(
        tool_name, tool_args, tool_result, execution_time_ms
    ))
    print("=" * 60 + "\n")


def extract_bee_citations_from_response(
    agent_response: Any,
    tools_registry: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Extract citation metadata from a BeeAI agent response.
    
    This function parses the agent response to find tool execution
    information and generates citation metadata.
    
    Args:
        agent_response: Response object from RequirementAgent.run()
        tools_registry: Dict mapping tool names to tool instances
    
    Returns:
        List of citation metadata dicts
    
    Example:
        ```python
        from tools import get_all_tools
        
        tools = {t.name: t for t in get_all_tools()}
        response = await agent.run(prompt="Search for Python")
        
        citations = extract_bee_citations_from_response(response, tools)
        ```
    """
    citations = []
    
    # Check if response has iteration/step data
    if not hasattr(agent_response, 'iterations'):
        return citations
    
    iterations = agent_response.iterations or []
    
    for iteration in iterations:
        # Check for tool calls in the iteration
        if hasattr(iteration, 'tool_calls'):
            for tool_call in iteration.tool_calls:
                tool_name = getattr(tool_call, 'tool_name', None) or getattr(tool_call, 'name', None)
                
                if not tool_name:
                    continue
                
                # Get the tool instance from registry
                tool_instance = tools_registry.get(tool_name)
                
                if tool_instance:
                    # Extract args and result
                    tool_args = getattr(tool_call, 'args', {}) or getattr(tool_call, 'input', {})
                    tool_result = getattr(tool_call, 'result', '') or getattr(tool_call, 'output', '')
                    
                    # Generate citation metadata using tool's method
                    citation_metadata = tool_instance.get_citation_metadata(
                        tool_args,
                        tool_result
                    )
                    
                    citations.append(citation_metadata)
        
        # Alternative: check for tool_results attribute
        elif hasattr(iteration, 'tool_results'):
            for result in iteration.tool_results:
                tool_name = getattr(result, 'tool_name', None)
                
                if tool_name and tool_name in tools_registry:
                    tool_instance = tools_registry[tool_name]
                    tool_args = getattr(result, 'args', {})
                    tool_output = getattr(result, 'output', '')
                    
                    citation_metadata = tool_instance.get_citation_metadata(
                        tool_args,
                        tool_output
                    )
                    
                    citations.append(citation_metadata)
    
    return citations


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "format_bee_citation",
    "format_bee_citations_for_beeai",
    "format_bee_tool_data_for_logging",
    "print_bee_tool_execution",
    "extract_bee_citations_from_response",
]
