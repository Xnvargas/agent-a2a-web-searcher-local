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
# A2A COMPLIANT PART CREATORS
# =============================================================================
# These functions create A2A protocol-compliant message parts that frontends
# can parse to render different UI elements (reasoning accordion, tool cards, etc.)

def create_thinking_text_part(
    text: str,
    step_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create an A2A TextPart with thinking/reasoning metadata.
    
    The frontend can use metadata.content_type == 'thinking' to render
    this in a reasoning accordion or collapsible section.
    
    Args:
        text: The thinking/reasoning text content
        step_number: Optional step number for ordered display
        
    Returns:
        A2A TextPart dict: {"kind": "text", "text": ..., "metadata": {...}}
    """
    metadata = {"content_type": ContentType.THINKING}
    if step_number is not None:
        metadata["step"] = step_number
    
    return {
        "kind": "text",
        "text": text,
        "metadata": metadata
    }


def create_response_text_part(text: str) -> Dict[str, Any]:
    """
    Create an A2A TextPart for final response content.
    
    The frontend can use metadata.content_type == 'response' to render
    this as the main response text.
    
    Args:
        text: The response text content
        
    Returns:
        A2A TextPart dict: {"kind": "text", "text": ..., "metadata": {...}}
    """
    return {
        "kind": "text",
        "text": text,
        "metadata": {"content_type": ContentType.RESPONSE}
    }


def create_tool_call_data_part(
    tool_name: str,
    args: Dict[str, Any],
    tool_call_id: Optional[str] = None,
    status: str = "in_progress"
) -> Dict[str, Any]:
    """
    Create an A2A DataPart for tool call events.
    
    The frontend parses data.type == 'tool_call' to render a chain-of-thought
    invocation card with spinner while the tool executes.
    
    Args:
        tool_name: Name of the tool being called
        args: Arguments passed to the tool
        tool_call_id: Unique ID for the tool call (for matching results)
        status: Current status (in_progress, pending, etc.)
        
    Returns:
        A2A DataPart dict: {"kind": "data", "data": {"type": "tool_call", ...}}
    """
    data = {
        "type": "tool_call",
        "tool_name": tool_name,
        "args": args,
        "status": status
    }
    if tool_call_id:
        data["tool_call_id"] = tool_call_id
    
    return {
        "kind": "data",
        "data": data
    }


def create_tool_result_data_part(
    tool_name: str,
    result: Any,
    tool_call_id: Optional[str] = None,
    status: str = "success",
    truncate_at: int = 1000
) -> Dict[str, Any]:
    """
    Create an A2A DataPart for tool execution results.
    
    The frontend parses data.type == 'tool_result' to update the chain-of-thought
    card with a checkmark and expandable result content.
    
    Args:
        tool_name: Name of the tool that executed
        result: The result returned by the tool
        tool_call_id: Unique ID matching the original tool call
        status: Execution status (success, error, etc.)
        truncate_at: Max chars for result in data (full result can overflow)
        
    Returns:
        A2A DataPart dict: {"kind": "data", "data": {"type": "tool_result", ...}}
    """
    result_str = str(result)
    result_preview = result_str[:truncate_at] + "..." if len(result_str) > truncate_at else result_str
    
    data = {
        "type": "tool_result",
        "tool_name": tool_name,
        "result": result_preview,
        "result_length": len(result_str),
        "status": status
    }
    if tool_call_id:
        data["tool_call_id"] = tool_call_id
    
    return {
        "kind": "data",
        "data": data
    }


def create_status_text_part(
    message: str,
    state: str = "working"
) -> Dict[str, Any]:
    """
    Create an A2A TextPart for status updates.
    
    Args:
        message: Status message to display
        state: Current state (working, completed, error, etc.)
        
    Returns:
        A2A TextPart dict with status metadata
    """
    return {
        "kind": "text",
        "text": message,
        "metadata": {
            "content_type": ContentType.STATUS,
            "state": state
        }
    }
