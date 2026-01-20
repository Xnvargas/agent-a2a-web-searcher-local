"""
=============================================================================
A2A PARTS - Helpers for Creating A2A Protocol-Compliant Parts
=============================================================================

This module provides helper functions for creating A2A protocol-compliant
message parts that work with both:
1. AgentStack SDK trajectory extension
2. Standard A2A clients expecting DataPart format

DOCUMENTATION REFERENCES:
-------------------------
- A2A Protocol Types: https://github.com/a2aproject/a2a-python
- AgentStack SDK Types: https://github.com/i-am-bee/agentstack
- Carbon AI Chat Formats: https://github.com/carbon-design-system/carbon-ai-chat

FRONTEND COMPATIBILITY:
-----------------------
The Carbon AI Chat frontend expects tool calls in one of these formats:

1. DataPart with type field:
   {
     "kind": "data",
     "data": {
       "type": "tool_call",
       "tool_name": "...",
       "args": {...}
     }
   }

2. TextPart with content_type metadata:
   {
     "kind": "text",
     "text": "...",
     "metadata": {
       "content_type": "tool_call"
     }
   }

This module creates DataPart format for maximum compatibility.

=============================================================================
"""

from typing import Any, Dict, List, Optional, Generator
import json

# Import A2A types
# Reference: https://github.com/a2aproject/a2a-python
try:
    from a2a.types import DataPart, TextPart, Part
except ImportError:
    # Fallback if a2a-sdk not installed
    DataPart = dict
    TextPart = dict
    Part = dict


# =============================================================================
# CONTENT TYPE CONSTANTS
# =============================================================================
# These match what the frontend translator expects
# Reference: agent-client-zero/lib/translator/a2a-to-carbon.ts

class A2AContentType:
    """Content type values for A2A DataPart.data.type field."""
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    REASONING_STEP = "reasoning_step"  # Batched post-tool reasoning steps
    RESPONSE = "response"
    STATUS = "status"


# =============================================================================
# DATA PART CREATORS
# =============================================================================

def create_tool_call_data_part(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> DataPart:
    """
    Create an A2A DataPart for a tool call event.

    This format is directly compatible with Carbon AI Chat's chain_of_thought
    rendering without needing trajectory metadata parsing.

    Reference:
    - Carbon scenarios.ts: https://github.com/carbon-design-system/carbon-ai-chat/blob/main/examples/react/reasoning-and-chain-of-thought/src/scenarios.ts
    - Frontend translator: agent-client-zero/lib/translator/a2a-to-carbon.ts

    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        tool_call_id: Optional unique ID for the tool call
        title: Optional display title (defaults to "Calling {tool_name}")
        description: Optional description of the tool action

    Returns:
        A2A DataPart object ready to be yielded

    Example:
        >>> part = create_tool_call_data_part(
        ...     tool_name="firecrawl_scrape",
        ...     args={"url": "https://example.com"},
        ...     tool_call_id="call_123"
        ... )
        >>> yield part
    """
    data = {
        "type": A2AContentType.TOOL_CALL,
        "tool_name": tool_name,
        "args": args,
        "title": title or f"Calling {tool_name}",
    }

    if tool_call_id:
        data["tool_call_id"] = tool_call_id
    if description:
        data["description"] = description

    # Return as DataPart (or dict if a2a-sdk not available)
    if isinstance(DataPart, type) and DataPart != dict:
        return DataPart(data=data)
    return {"kind": "data", "data": data}


def create_tool_result_data_part(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    error: bool = False,
    truncate_at: int = 1000
) -> DataPart:
    """
    Create an A2A DataPart for a tool execution result.

    This format is directly compatible with Carbon AI Chat's chain_of_thought
    rendering with success/error status indicators.

    Reference:
    - Carbon ChainOfThoughtStepStatus: https://github.com/carbon-design-system/carbon-ai-chat
    - Frontend translator expects: status = "success" | "error"

    Args:
        tool_name: Name of the tool that was executed
        result: The result returned by the tool
        tool_call_id: Optional unique ID matching the tool call
        title: Optional display title (defaults to "{tool_name} completed")
        description: Optional description
        error: Whether the tool execution resulted in an error
        truncate_at: Max chars for result in data (full result in description)

    Returns:
        A2A DataPart object ready to be yielded

    Example:
        >>> part = create_tool_result_data_part(
        ...     tool_name="firecrawl_scrape",
        ...     result={"content": "Page content..."},
        ...     tool_call_id="call_123",
        ...     error=False
        ... )
        >>> yield part
    """
    result_str = str(result) if not isinstance(result, str) else result
    result_preview = result_str[:truncate_at] + "..." if len(result_str) > truncate_at else result_str

    status = "error" if error else "success"
    default_title = f"{tool_name} {'failed' if error else 'completed'}"

    data = {
        "type": A2AContentType.TOOL_RESULT,
        "tool_name": tool_name,
        "result": result_preview,
        "title": title or default_title,
        "status": status,
        "error": error,
    }

    if tool_call_id:
        data["tool_call_id"] = tool_call_id
    if description:
        data["description"] = description

    # Return as DataPart
    if isinstance(DataPart, type) and DataPart != dict:
        return DataPart(data=data)
    return {"kind": "data", "data": data}


def create_thinking_text_part(
    content: str,
    step_number: Optional[int] = None,
    title: Optional[str] = None
) -> TextPart:
    """
    Create an A2A TextPart for thinking/reasoning content.

    This uses the metadata.content_type format that the frontend
    translator checks for reasoning_steps rendering.

    Reference:
    - Frontend translateMetadataPart(): agent-client-zero/lib/translator/a2a-to-carbon.ts
    - Carbon ReasoningSteps: https://github.com/carbon-design-system/carbon-ai-chat

    Args:
        content: The thinking/reasoning text content
        step_number: Optional step number for ordered display
        title: Optional title for the reasoning step (e.g., "Analyzing Query")

    Returns:
        A2A TextPart object ready to be yielded
    """
    metadata = {
        "content_type": A2AContentType.THINKING,
    }
    if step_number is not None:
        metadata["step"] = step_number
    if title is not None:
        metadata["title"] = title

    # Return as TextPart
    if isinstance(TextPart, type) and TextPart != dict:
        return TextPart(text=content, metadata=metadata)
    return {"kind": "text", "text": content, "metadata": metadata}


def create_response_text_part(content: str) -> TextPart:
    """
    Create an A2A TextPart for response content.

    Args:
        content: The response text content

    Returns:
        A2A TextPart object ready to be yielded
    """
    metadata = {
        "content_type": A2AContentType.RESPONSE,
    }

    if isinstance(TextPart, type) and TextPart != dict:
        return TextPart(text=content, metadata=metadata)
    return {"kind": "text", "text": content, "metadata": metadata}


# =============================================================================
# AGENTMESSAGE HELPERS
# =============================================================================
# For use with agentstack_sdk.a2a.types.AgentMessage

def create_tool_call_agent_message(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None
):
    """
    Create an AgentMessage containing a tool call DataPart.

    This is the recommended way to emit tool calls when using AgentStack SDK,
    as it creates proper A2A-compliant parts.

    Reference:
    - AgentStack messages guide: https://raw.githubusercontent.com/i-am-bee/agentstack/main/docs/stable/agent-integration/messages.mdx

    Example:
        >>> from agentstack_sdk.a2a.types import AgentMessage
        >>> msg = create_tool_call_agent_message(
        ...     tool_name="searx_search",
        ...     args={"query": "python best practices"},
        ...     tool_call_id="call_456"
        ... )
        >>> yield msg
    """
    try:
        from agentstack_sdk.a2a.types import AgentMessage
        part = create_tool_call_data_part(tool_name, args, tool_call_id)
        return AgentMessage(parts=[part])
    except ImportError:
        # Return raw dict if SDK not available
        return create_tool_call_data_part(tool_name, args, tool_call_id)


def create_tool_result_agent_message(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    error: bool = False
):
    """
    Create an AgentMessage containing a tool result DataPart.

    Example:
        >>> msg = create_tool_result_agent_message(
        ...     tool_name="searx_search",
        ...     result={"results": [...]},
        ...     tool_call_id="call_456"
        ... )
        >>> yield msg
    """
    try:
        from agentstack_sdk.a2a.types import AgentMessage
        part = create_tool_result_data_part(tool_name, result, tool_call_id, error=error)
        return AgentMessage(parts=[part])
    except ImportError:
        return create_tool_result_data_part(tool_name, result, tool_call_id, error=error)


# =============================================================================
# DUAL-EMIT HELPERS
# =============================================================================
# These emit both trajectory metadata AND DataPart for maximum compatibility

def emit_tool_call_with_trajectory(
    trajectory_server,
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None
) -> Generator[Any, None, None]:
    """
    Emit both trajectory metadata AND a DataPart for a tool call.

    This ensures compatibility with:
    1. AgentStack's trajectory extension UI
    2. Standard A2A clients expecting DataPart format
    3. Carbon AI Chat's chain_of_thought rendering

    Usage in agent:
        >>> for item in emit_tool_call_with_trajectory(
        ...     trajectory, "firecrawl_scrape", {"url": "..."}
        ... ):
        ...     yield item

    Args:
        trajectory_server: The TrajectoryExtensionServer instance
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        tool_call_id: Optional unique ID for the tool call

    Yields:
        1. Trajectory metadata (for AgentStack UI)
        2. DataPart (for standard A2A clients)
    """
    # Format trajectory title and content
    title = f"Calling {tool_name}"
    content = f"**Arguments:**\n```json\n{json.dumps(args, indent=2)}\n```"
    if tool_call_id:
        content = f"**Tool Call ID:** `{tool_call_id}`\n\n{content}"

    # 1. Yield trajectory metadata (for AgentStack UI)
    yield trajectory_server.trajectory_metadata(
        title=title,
        content=content
    )

    # 2. Yield DataPart (for standard A2A clients / Carbon AI Chat)
    yield create_tool_call_data_part(
        tool_name=tool_name,
        args=args,
        tool_call_id=tool_call_id,
        title=title
    )


def emit_tool_result_with_trajectory(
    trajectory_server,
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    status: str = "success"
) -> Generator[Any, None, None]:
    """
    Emit both trajectory metadata AND a DataPart for a tool result.

    Usage in agent:
        >>> for item in emit_tool_result_with_trajectory(
        ...     trajectory, "firecrawl_scrape", result_data
        ... ):
        ...     yield item

    Args:
        trajectory_server: The TrajectoryExtensionServer instance
        tool_name: Name of the tool that was executed
        result: The result returned by the tool
        tool_call_id: Optional unique ID matching the tool call
        status: Execution status ("success" or "error")

    Yields:
        1. Trajectory metadata (for AgentStack UI)
        2. DataPart (for standard A2A clients)
    """
    error = status == "error"

    # Format trajectory title and content
    status_emoji = "X" if error else "+"
    title = f"{tool_name} {'failed' if error else 'completed'}"

    result_str = str(result)
    result_preview = result_str[:500] + "..." if len(result_str) > 500 else result_str
    content = f"**Status:** [{status_emoji}] {status}\n\n**Result:**\n```\n{result_preview}\n```"
    if tool_call_id:
        content = f"**Tool Call ID:** `{tool_call_id}`\n\n{content}"

    # 1. Yield trajectory metadata (for AgentStack UI)
    yield trajectory_server.trajectory_metadata(
        title=title,
        content=content
    )

    # 2. Yield DataPart (for standard A2A clients / Carbon AI Chat)
    yield create_tool_result_data_part(
        tool_name=tool_name,
        result=result,
        tool_call_id=tool_call_id,
        title=title,
        error=error
    )


# =============================================================================
# AGENTMESSAGE WRAPPER HELPERS
# =============================================================================
# These functions wrap TextPart/DataPart in AgentMessage for proper A2A
# protocol serialization. Use these when yielding from the agent instead
# of the raw create_*_part() functions.

def emit_thinking_part(
    content: str,
    step_number: Optional[int] = None,
    title: Optional[str] = None
):
    """
    Emit a thinking TextPart wrapped in AgentMessage for proper A2A serialization.

    Use this instead of create_thinking_text_part() when yielding from the agent.
    The AgentStack SDK requires AgentMessage objects to properly serialize parts
    into the A2A protocol stream.

    Args:
        content: The thinking/reasoning text content
        step_number: Optional step number for ordered display
        title: Optional title for the reasoning step

    Returns:
        AgentMessage containing the thinking TextPart

    Example:
        >>> yield emit_thinking_part("Analyzing the query...", step_number=1)
    """
    try:
        from agentstack_sdk.a2a.types import AgentMessage
        part = create_thinking_text_part(content, step_number, title)
        return AgentMessage(parts=[part])
    except ImportError:
        # Fallback if SDK not available (standalone testing)
        return create_thinking_text_part(content, step_number, title)


def emit_response_part(content: str):
    """
    Emit a response TextPart wrapped in AgentMessage for proper A2A serialization.

    Use this instead of create_response_text_part() when yielding from the agent.
    The AgentStack SDK requires AgentMessage objects to properly serialize parts
    into the A2A protocol stream.

    Args:
        content: The response text content

    Returns:
        AgentMessage containing the response TextPart

    Example:
        >>> yield emit_response_part("Based on my analysis, here are the results...")
    """
    try:
        from agentstack_sdk.a2a.types import AgentMessage
        part = create_response_text_part(content)
        return AgentMessage(parts=[part])
    except ImportError:
        # Fallback if SDK not available (standalone testing)
        return create_response_text_part(content)


def emit_reasoning_step(
    title: str,
    content: str,
    step_number: Optional[int] = None
):
    """
    Emit a complete reasoning step (non-streaming) wrapped in AgentMessage.

    Used for post-tool reasoning that should appear as a discrete
    collapsible section in the reasoning accordion. Unlike emit_thinking_part()
    which streams token-by-token, this emits complete reasoning blocks that
    were accumulated during tool execution phases.

    This enables the UI to show:
    - Phase 1 (initial thinking): Streamed via emit_thinking_part() -> reasoning.content
    - Phase 2 (post-tool analysis): Batched via emit_reasoning_step() -> reasoning.steps[]
    - Phase 3 (final response): Streamed via emit_response_part() -> main response

    Args:
        title: Step title (e.g., "Analyzing firecrawl_scrape results")
        content: Full content of this reasoning step
        step_number: Optional step number for ordering

    Returns:
        AgentMessage containing the reasoning step TextPart

    Example:
        >>> yield emit_reasoning_step(
        ...     title="Analyzing search results",
        ...     content="The search returned 5 relevant results...",
        ...     step_number=1
        ... )
    """
    metadata = {
        "content_type": A2AContentType.REASONING_STEP,
        "title": title,
    }
    if step_number is not None:
        metadata["step"] = step_number

    try:
        from agentstack_sdk.a2a.types import AgentMessage
        if isinstance(TextPart, type) and TextPart != dict:
            part = TextPart(text=content, metadata=metadata)
        else:
            part = {"kind": "text", "text": content, "metadata": metadata}
        return AgentMessage(parts=[part])
    except ImportError:
        # Fallback if SDK not available (standalone testing)
        if isinstance(TextPart, type) and TextPart != dict:
            return TextPart(text=content, metadata=metadata)
        return {"kind": "text", "text": content, "metadata": metadata}


def emit_tool_call_part(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None,
    title: Optional[str] = None
):
    """
    Emit a tool call DataPart wrapped in AgentMessage for proper A2A serialization.

    Note: For full compatibility with AgentStack trajectory UI, use
    emit_tool_call_with_trajectory() instead, which emits both trajectory
    metadata AND the DataPart.

    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        tool_call_id: Optional unique ID for the tool call
        title: Optional display title

    Returns:
        AgentMessage containing the tool call DataPart
    """
    try:
        from agentstack_sdk.a2a.types import AgentMessage
        part = create_tool_call_data_part(tool_name, args, tool_call_id, title)
        return AgentMessage(parts=[part])
    except ImportError:
        return create_tool_call_data_part(tool_name, args, tool_call_id, title)


def emit_tool_result_part(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    error: bool = False
):
    """
    Emit a tool result DataPart wrapped in AgentMessage for proper A2A serialization.

    Note: For full compatibility with AgentStack trajectory UI, use
    emit_tool_result_with_trajectory() instead, which emits both trajectory
    metadata AND the DataPart.

    Args:
        tool_name: Name of the tool that was executed
        result: The result returned by the tool
        tool_call_id: Optional unique ID matching the tool call
        error: Whether the tool execution resulted in an error

    Returns:
        AgentMessage containing the tool result DataPart
    """
    try:
        from agentstack_sdk.a2a.types import AgentMessage
        part = create_tool_result_data_part(tool_name, result, tool_call_id, error=error)
        return AgentMessage(parts=[part])
    except ImportError:
        return create_tool_result_data_part(tool_name, result, tool_call_id, error=error)
