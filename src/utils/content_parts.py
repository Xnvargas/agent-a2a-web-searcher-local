"""
=============================================================================
CONTENT PARTS - Typed Content Helpers for A2A Streaming
=============================================================================

This module provides helper functions and constants for creating typed content
that enables visual differentiation in Carbon frontend (reasoning, tool calls,
responses).

PROTOCOL COMPLIANCE:
--------------------

Uses standard A2A Part.metadata field for semantic content typing:
- TextPart: kind="text" with metadata.content_type
- DataPart: kind="data" with structured tool info

FRONTEND MAPPING:
-----------------

| Server content_type | Carbon UI Element                      |
|---------------------|----------------------------------------|
| thinking            | reasoning.steps / reasoning.content     |
| tool_call           | chain_of_thought tool invocation card   |
| tool_result         | chain_of_thought result expansion       |
| response            | Main response text                      |
| status              | Progress indicator / status badge       |

=============================================================================
"""

import json
from typing import Any, Dict, Optional
from dataclasses import dataclass


# =============================================================================
# CONTENT TYPE CONSTANTS
# =============================================================================

class ContentType:
    """Content type constants for frontend visual differentiation."""
    THINKING = "thinking"       # For reasoning/thinking steps (before tool calls)
    RESPONSE = "response"       # For final response text (after tool calls)
    TOOL_CALL = "tool_call"     # For tool invocation events
    TOOL_RESULT = "tool_result" # For tool execution results
    STATUS = "status"           # For status messages


# =============================================================================
# TYPED CONTENT STRUCTURES
# =============================================================================

@dataclass
class TypedContent:
    """
    Container for typed content with metadata.
    
    This structure can be serialized and passed through the streaming pipeline
    to provide semantic information to the frontend.
    """
    content: str
    content_type: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "content_type": self.content_type,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class ToolCallInfo:
    """Structured information about a tool call."""
    tool_name: str
    args: Dict[str, Any]
    tool_call_id: Optional[str] = None
    status: str = "in_progress"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "type": "tool_call",
            "tool_name": self.tool_name,
            "args": self.args,
            "status": self.status
        }
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass  
class ToolResultInfo:
    """Structured information about a tool execution result."""
    tool_name: str
    result: Any
    tool_call_id: Optional[str] = None
    status: str = "success"
    truncate_at: int = 500
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result_str = str(self.result)
        result_preview = result_str[:self.truncate_at] + "..." if len(result_str) > self.truncate_at else result_str
        
        data = {
            "type": "tool_result",
            "tool_name": self.tool_name,
            "result_preview": result_preview,
            "result_length": len(result_str),
            "status": self.status
        }
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_thinking_metadata(
    text: str, 
    step_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create metadata dict for thinking/reasoning content.
    
    Args:
        text: The thinking/reasoning text
        step_number: Optional step number for ordered reasoning display
        
    Returns:
        Metadata dictionary with content_type="thinking"
    """
    metadata = {
        "content_type": ContentType.THINKING,
        "text_preview": text[:100] + "..." if len(text) > 100 else text
    }
    if step_number is not None:
        metadata["step"] = step_number
    return metadata


def create_response_metadata(text: str) -> Dict[str, Any]:
    """
    Create metadata dict for final response content.
    
    Args:
        text: The response text
        
    Returns:
        Metadata dictionary with content_type="response"
    """
    return {
        "content_type": ContentType.RESPONSE,
        "text_length": len(text)
    }


def create_tool_call_metadata(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None,
    status: str = "in_progress"
) -> Dict[str, Any]:
    """
    Create metadata dict for tool call events.
    
    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        tool_call_id: Optional unique ID for the tool call
        status: Status of the call (in_progress, pending, etc.)
        
    Returns:
        Metadata dictionary with content_type="tool_call" and structured data
    """
    return {
        "content_type": ContentType.TOOL_CALL,
        "tool_data": ToolCallInfo(
            tool_name=tool_name,
            args=args,
            tool_call_id=tool_call_id,
            status=status
        ).to_dict()
    }


def create_tool_result_metadata(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    status: str = "success",
    truncate_at: int = 500
) -> Dict[str, Any]:
    """
    Create metadata dict for tool execution results.
    
    Args:
        tool_name: Name of the tool that was executed
        result: The result returned by the tool
        tool_call_id: Optional unique ID matching the tool call
        status: Execution status (success, error, etc.)
        truncate_at: Max chars for result preview
        
    Returns:
        Metadata dictionary with content_type="tool_result" and structured data
    """
    return {
        "content_type": ContentType.TOOL_RESULT,
        "tool_data": ToolResultInfo(
            tool_name=tool_name,
            result=result,
            tool_call_id=tool_call_id,
            status=status,
            truncate_at=truncate_at
        ).to_dict()
    }


def create_status_metadata(
    message: str,
    state: str = "working"
) -> Dict[str, Any]:
    """
    Create metadata dict for status updates.
    
    Args:
        message: Status message text
        state: Current state (working, completed, error, etc.)
        
    Returns:
        Metadata dictionary with content_type="status"
    """
    return {
        "content_type": ContentType.STATUS,
        "state": state,
        "message": message
    }


# =============================================================================
# TRAJECTORY METADATA FORMATTERS
# =============================================================================

def format_thinking_trajectory(
    content: str,
    step_number: Optional[int] = None
) -> tuple[str, str]:
    """
    Format thinking content for trajectory metadata.

    Returns:
        Tuple of (title, content_json) for trajectory.trajectory_metadata()
    """
    title = f"Thinking Step {step_number}" if step_number else "Reasoning"
    metadata = create_thinking_metadata(content, step_number)

    return title, json.dumps({
        "content": content,
        **metadata
    })


def format_tool_call_trajectory(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None
) -> tuple[str, str]:
    """
    Format tool call for trajectory metadata.

    Returns:
        Tuple of (title, content_json) for trajectory.trajectory_metadata()
    """
    title = f"Tool Call: {tool_name}"
    metadata = create_tool_call_metadata(tool_name, args, tool_call_id)

    return title, json.dumps(metadata)


def format_tool_result_trajectory(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    status: str = "success"
) -> tuple[str, str]:
    """
    Format tool result for trajectory metadata.

    Returns:
        Tuple of (title, content_json) for trajectory.trajectory_metadata()
    """
    title = f"Tool Result: {tool_name}"
    metadata = create_tool_result_metadata(tool_name, result, tool_call_id, status)

    return title, json.dumps(metadata)


# =============================================================================
# URI-KEYED TRAJECTORY METADATA (A2A Protocol Compliant)
# =============================================================================

from .extension_uris import ExtensionURIs, create_extension_metadata


def create_trajectory_metadata(
    title: str,
    content: str,
    group_id: Optional[str] = None,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create trajectory metadata in URI-keyed format for A2A protocol.

    Returns metadata keyed by the trajectory extension URI for client parsing.

    Args:
        title: Display title for the trajectory step
        content: Content to display (can be markdown)
        group_id: Optional ID to group related trajectory steps
        content_type: Optional content type for semantic categorization

    Returns:
        Dictionary with trajectory extension URI as key

    Example:
        ```python
        metadata = create_trajectory_metadata(
            title="Calling search tool",
            content="```json\\n{\"query\": \"python\"}\\n```",
            group_id="tool-search-123"
        )
        ```
    """
    trajectory_data = {
        "title": title,
        "content": content,
    }

    if group_id:
        trajectory_data["group_id"] = group_id
    if content_type:
        trajectory_data["content_type"] = content_type

    return create_extension_metadata(ExtensionURIs.TRAJECTORY, trajectory_data)


def create_thinking_trajectory_metadata(
    content: str,
    step_number: Optional[int] = None,
    group_id: str = "reasoning"
) -> Dict[str, Any]:
    """
    Create URI-keyed trajectory metadata for thinking/reasoning content.

    Args:
        content: The thinking/reasoning content
        step_number: Optional step number
        group_id: Group ID for relating thinking steps (default: "reasoning")

    Returns:
        Dictionary with trajectory extension URI as key
    """
    title = f"Thinking Step {step_number}" if step_number else "Reasoning"

    return create_trajectory_metadata(
        title=title,
        content=content,
        group_id=group_id,
        content_type=ContentType.THINKING
    )


def create_tool_call_trajectory_metadata(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create URI-keyed trajectory metadata for tool calls.

    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        tool_call_id: Optional unique ID for the tool call

    Returns:
        Dictionary with trajectory extension URI as key

    Example:
        ```python
        metadata = create_tool_call_trajectory_metadata(
            tool_name="firecrawl_scrape",
            args={"url": "https://example.com"},
            tool_call_id="call_123"
        )
        ```
    """
    content = f"**Arguments:**\n```json\n{json.dumps(args, indent=2)}\n```"
    group_id = f"tool-{tool_call_id or tool_name}"

    return create_trajectory_metadata(
        title=f"Calling {tool_name}",
        content=content,
        group_id=group_id,
        content_type=ContentType.TOOL_CALL
    )


def create_tool_result_trajectory_metadata(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    status: str = "success",
    truncate_at: int = 500
) -> Dict[str, Any]:
    """
    Create URI-keyed trajectory metadata for tool results.

    Args:
        tool_name: Name of the tool that was executed
        result: The result returned by the tool
        tool_call_id: Optional unique ID matching the tool call
        status: Execution status (success, error, etc.)
        truncate_at: Max characters for result preview

    Returns:
        Dictionary with trajectory extension URI as key
    """
    result_str = str(result)
    result_preview = result_str[:truncate_at] + "..." if len(result_str) > truncate_at else result_str

    status_emoji = "" if status == "success" else ""
    content = f"**Status:** {status_emoji} {status}\n\n**Result:**\n```\n{result_preview}\n```"
    group_id = f"tool-{tool_call_id or tool_name}"

    return create_trajectory_metadata(
        title=f"{tool_name} Result",
        content=content,
        group_id=group_id,
        content_type=ContentType.TOOL_RESULT
    )


def create_status_trajectory_metadata(
    message: str,
    state: str = "working"
) -> Dict[str, Any]:
    """
    Create URI-keyed trajectory metadata for status updates.

    Args:
        message: Status message
        state: Current state (working, completed, error, etc.)

    Returns:
        Dictionary with trajectory extension URI as key
    """
    state_emoji = {
        "working": "",
        "completed": "",
        "error": "",
        "waiting": "",
        "pending": ""
    }.get(state, "")

    return create_trajectory_metadata(
        title=f"{state_emoji} {message}",
        content=f"State: {state}",
        content_type=ContentType.STATUS
    )
