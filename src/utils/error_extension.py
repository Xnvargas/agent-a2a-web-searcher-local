"""
=============================================================================
ERROR EXTENSION - Structured Error Reporting for A2A Protocol
=============================================================================

This module provides utilities for creating structured error metadata that
follows the A2A error extension specification.

USAGE:
------

```python
from utils.error_extension import create_error_metadata, ErrorInfo
import traceback

try:
    # Agent execution
    result = await dangerous_operation()
except Exception as e:
    error_metadata = create_error_metadata(
        message=str(e),
        code=type(e).__name__,
        stacktrace=traceback.format_exc(),
        context={"operation": "dangerous_operation", "attempt": 1}
    )

    # Yield error with proper metadata
    yield AgentMessage(
        text=f"An error occurred: {str(e)}",
        metadata=error_metadata
    )
```

A2A PROTOCOL COMPLIANCE:
------------------------

This module supports the A2A error extension by providing:
- URI-keyed metadata format for client parsing
- Structured error information with code, message, stacktrace
- Optional context data for debugging

FRONTEND MAPPING:
-----------------

The client error extension parser expects:
- message: Human-readable error message
- code: Error code or exception type
- stacktrace: Optional stack trace for debugging
- context: Optional additional context

=============================================================================
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import traceback as tb

from .extension_uris import ExtensionURIs, create_extension_metadata


# =============================================================================
# ERROR DATA STRUCTURES
# =============================================================================

@dataclass
class ErrorInfo:
    """
    Structured error information for A2A protocol compliance.

    Attributes:
        message: Human-readable error message
        code: Error code or exception type name
        stacktrace: Optional stack trace for debugging
        context: Optional dictionary with additional debugging context
        recoverable: Whether the error is recoverable
        suggested_action: Optional suggestion for how to handle the error
    """
    message: str
    code: Optional[str] = None
    stacktrace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    recoverable: bool = False
    suggested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        data = {"message": self.message}

        if self.code:
            data["code"] = self.code
        if self.stacktrace:
            data["stacktrace"] = self.stacktrace
        if self.context:
            data["context"] = self.context
        if self.recoverable:
            data["recoverable"] = self.recoverable
        if self.suggested_action:
            data["suggested_action"] = self.suggested_action

        return data


# =============================================================================
# A2A PROTOCOL ERROR METADATA HELPERS
# =============================================================================

def create_error_metadata(
    message: str,
    code: Optional[str] = None,
    stacktrace: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    recoverable: bool = False,
    suggested_action: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create error metadata in the A2A protocol format.

    Returns metadata keyed by the error extension URI for client parsing.

    Args:
        message: Human-readable error message
        code: Error code or exception type name
        stacktrace: Optional stack trace for debugging
        context: Optional dictionary with additional context
        recoverable: Whether the error is recoverable
        suggested_action: Optional suggestion for resolution

    Returns:
        Dictionary with error extension URI as key and error data as value

    Example:
        ```python
        metadata = create_error_metadata(
            message="Failed to connect to API",
            code="ConnectionError",
            context={"url": "https://api.example.com", "timeout": 30}
        )
        # Returns:
        # {
        #     "https://a2a-extensions.../error/v1": {
        #         "message": "Failed to connect to API",
        #         "code": "ConnectionError",
        #         "context": {...}
        #     }
        # }
        ```
    """
    error_data = {"message": message}

    if code:
        error_data["code"] = code
    if stacktrace:
        error_data["stacktrace"] = stacktrace
    if context:
        error_data["context"] = context
    if recoverable:
        error_data["recoverable"] = recoverable
    if suggested_action:
        error_data["suggested_action"] = suggested_action

    return create_extension_metadata(ExtensionURIs.ERROR, error_data)


def create_error_metadata_from_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    include_stacktrace: bool = True,
    recoverable: bool = False
) -> Dict[str, Any]:
    """
    Create error metadata from a Python exception.

    Convenience function that extracts information from an exception object.

    Args:
        exception: The Python exception to create metadata from
        context: Optional additional context
        include_stacktrace: Whether to include the stack trace
        recoverable: Whether the error is recoverable

    Returns:
        Dictionary with error extension URI as key and error data as value

    Example:
        ```python
        try:
            result = risky_operation()
        except Exception as e:
            metadata = create_error_metadata_from_exception(
                e,
                context={"operation": "risky_operation"}
            )
        ```
    """
    stacktrace = tb.format_exc() if include_stacktrace else None

    return create_error_metadata(
        message=str(exception),
        code=type(exception).__name__,
        stacktrace=stacktrace,
        context=context,
        recoverable=recoverable
    )


def create_tool_error_metadata(
    tool_name: str,
    tool_args: Dict[str, Any],
    error: Exception,
    tool_call_id: Optional[str] = None,
    include_stacktrace: bool = True
) -> Dict[str, Any]:
    """
    Create error metadata specifically for tool execution failures.

    Args:
        tool_name: Name of the tool that failed
        tool_args: Arguments that were passed to the tool
        error: The exception that was raised
        tool_call_id: Optional ID of the tool call
        include_stacktrace: Whether to include the stack trace

    Returns:
        Dictionary with error extension URI as key and error data as value

    Example:
        ```python
        try:
            result = await tool.execute(args)
        except Exception as e:
            metadata = create_tool_error_metadata(
                tool_name="firecrawl_scrape",
                tool_args={"url": "https://example.com"},
                error=e,
                tool_call_id="call_123"
            )
        ```
    """
    context = {
        "tool_name": tool_name,
        "tool_args": tool_args,
    }

    if tool_call_id:
        context["tool_call_id"] = tool_call_id

    return create_error_metadata_from_exception(
        error,
        context=context,
        include_stacktrace=include_stacktrace,
        recoverable=True  # Tool errors are typically recoverable
    )


def create_validation_error_metadata(
    field_errors: Dict[str, List[str]],
    message: str = "Validation failed"
) -> Dict[str, Any]:
    """
    Create error metadata for validation failures.

    Args:
        field_errors: Dictionary mapping field names to list of error messages
        message: Overall error message

    Returns:
        Dictionary with error extension URI as key and error data as value

    Example:
        ```python
        metadata = create_validation_error_metadata(
            field_errors={
                "url": ["Invalid URL format", "URL must use HTTPS"],
                "timeout": ["Must be positive integer"]
            }
        )
        ```
    """
    return create_error_metadata(
        message=message,
        code="ValidationError",
        context={"field_errors": field_errors},
        recoverable=True,
        suggested_action="Please correct the validation errors and try again"
    )


# =============================================================================
# ERROR SEVERITY HELPERS
# =============================================================================

class ErrorSeverity:
    """Error severity levels for categorization."""
    INFO = "info"           # Informational, not a real error
    WARNING = "warning"     # Warning, operation continued
    ERROR = "error"         # Error, operation failed but recoverable
    CRITICAL = "critical"   # Critical error, may require intervention


def create_error_metadata_with_severity(
    message: str,
    severity: str = ErrorSeverity.ERROR,
    code: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create error metadata with severity level.

    Args:
        message: Human-readable error message
        severity: Error severity level from ErrorSeverity class
        code: Error code or exception type name
        context: Optional additional context

    Returns:
        Dictionary with error extension URI as key and error data as value
    """
    full_context = context or {}
    full_context["severity"] = severity

    recoverable = severity in [ErrorSeverity.INFO, ErrorSeverity.WARNING, ErrorSeverity.ERROR]

    return create_error_metadata(
        message=message,
        code=code,
        context=full_context,
        recoverable=recoverable
    )
