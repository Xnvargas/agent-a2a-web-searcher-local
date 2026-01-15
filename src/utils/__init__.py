"""
=============================================================================
UTILS PACKAGE - Agent Factory and Utilities
=============================================================================

This package provides utilities for creating LangGraph agents, citation
handling, and A2A protocol extensions.

MAIN EXPORTS:
-------------

- create_langgraph_agent: Factory function to create agents with tools
- A2A Extensions: Citation, Error, Form, Trajectory utilities
- Extension URIs: Centralized URI constants for A2A protocol

USAGE:
------

```python
from utils import create_langgraph_agent
from tools import get_all_tools

# Create agent with all registered tools
agent = create_langgraph_agent(
    api_model="granite-4:micro-h",
    api_key="your-key",
    api_base="http://localhost:11434/v1",
    tools=get_all_tools()
)

# Or create with specific tools
from tools import get_tool_by_name
custom_tools = [
    get_tool_by_name("firecrawl_scrape"),
    get_tool_by_name("searx_search"),
]
agent = create_langgraph_agent(..., tools=custom_tools)

# A2A Extensions Usage
from utils import (
    ExtensionURIs,
    create_citation_metadata,
    create_error_metadata,
    create_form_request_metadata,
    create_trajectory_metadata
)
```

=============================================================================
"""

# -----------------------------------------------------------------------------
# Main factory function - LangGraph
# -----------------------------------------------------------------------------
from .langgraph_factory import create_langgraph_agent

# -----------------------------------------------------------------------------
# Content Parts - Typed content for streaming
# -----------------------------------------------------------------------------
from .content_parts import (
    ContentType,
    TypedContent,
    ToolCallInfo,
    ToolResultInfo,
    create_thinking_metadata,
    create_response_metadata,
    create_tool_call_metadata,
    create_tool_result_metadata,
    create_status_metadata,
    # Original trajectory formatters
    format_thinking_trajectory,
    format_tool_call_trajectory,
    format_tool_result_trajectory,
    # URI-keyed trajectory metadata (A2A Protocol)
    create_trajectory_metadata,
    create_thinking_trajectory_metadata,
    create_tool_call_trajectory_metadata,
    create_tool_result_trajectory_metadata,
    create_status_trajectory_metadata,
)

# -----------------------------------------------------------------------------
# BeeAI Framework factory function
# -----------------------------------------------------------------------------
from .bee_factory import (
    create_beeai_agent,
    create_beeai_llm,
    wrap_tools_for_beeai,
    run_beeai_agent,
)

# -----------------------------------------------------------------------------
# Extension URIs - Centralized A2A protocol URIs
# -----------------------------------------------------------------------------
from .extension_uris import (
    ExtensionURIs,
    create_extension_metadata,
    merge_extension_metadata,
)

# -----------------------------------------------------------------------------
# Citation utilities (LangGraph) - Enhanced with A2A protocol support
# -----------------------------------------------------------------------------
from .citations import (
    # Citation dataclass
    Citation,
    # A2A protocol citation metadata
    create_citation_metadata,
    calculate_citation_positions,
    find_text_spans_for_citation,
    # Original citation helpers
    format_citation,
    format_citations_for_beeai,
    format_tool_data_for_logging,
    print_tool_execution,
)

# -----------------------------------------------------------------------------
# Error Extension - Structured error handling for A2A protocol
# -----------------------------------------------------------------------------
from .error_extension import (
    ErrorInfo,
    ErrorSeverity,
    create_error_metadata,
    create_error_metadata_from_exception,
    create_tool_error_metadata,
    create_validation_error_metadata,
    create_error_metadata_with_severity,
)

# -----------------------------------------------------------------------------
# Form Extension - User input requests for A2A protocol
# -----------------------------------------------------------------------------
from .form_extension import (
    FieldType,
    FormField,
    SelectOption,
    create_form_request_metadata,
    # Convenience field builders
    text_field,
    textarea_field,
    select_field,
    checkbox_field,
    number_field,
    file_field,
    # Common form templates
    create_confirmation_form,
    create_api_key_form,
    create_options_selection_form,
)

# -----------------------------------------------------------------------------
# BeeAI Citation utilities
# -----------------------------------------------------------------------------
from .bee_citations import (
    format_bee_citation,
    format_bee_citations_for_beeai,
    format_bee_tool_data_for_logging,
    print_bee_tool_execution,
    extract_bee_citations_from_response,
)

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
__all__ = [
    # LangGraph Factory
    "create_langgraph_agent",

    # BeeAI Factory
    "create_beeai_agent",
    "create_beeai_llm",
    "wrap_tools_for_beeai",
    "run_beeai_agent",

    # Extension URIs
    "ExtensionURIs",
    "create_extension_metadata",
    "merge_extension_metadata",

    # Content Types
    "ContentType",
    "TypedContent",
    "ToolCallInfo",
    "ToolResultInfo",
    "create_thinking_metadata",
    "create_response_metadata",
    "create_tool_call_metadata",
    "create_tool_result_metadata",
    "create_status_metadata",

    # Trajectory Formatters (original)
    "format_thinking_trajectory",
    "format_tool_call_trajectory",
    "format_tool_result_trajectory",

    # Trajectory Metadata (URI-keyed A2A protocol)
    "create_trajectory_metadata",
    "create_thinking_trajectory_metadata",
    "create_tool_call_trajectory_metadata",
    "create_tool_result_trajectory_metadata",
    "create_status_trajectory_metadata",

    # Citation (A2A Protocol)
    "Citation",
    "create_citation_metadata",
    "calculate_citation_positions",
    "find_text_spans_for_citation",

    # Citation (Original)
    "format_citation",
    "format_citations_for_beeai",
    "format_tool_data_for_logging",
    "print_tool_execution",

    # Error Extension
    "ErrorInfo",
    "ErrorSeverity",
    "create_error_metadata",
    "create_error_metadata_from_exception",
    "create_tool_error_metadata",
    "create_validation_error_metadata",
    "create_error_metadata_with_severity",

    # Form Extension
    "FieldType",
    "FormField",
    "SelectOption",
    "create_form_request_metadata",
    "text_field",
    "textarea_field",
    "select_field",
    "checkbox_field",
    "number_field",
    "file_field",
    "create_confirmation_form",
    "create_api_key_form",
    "create_options_selection_form",

    # BeeAI Citations
    "format_bee_citation",
    "format_bee_citations_for_beeai",
    "format_bee_tool_data_for_logging",
    "print_bee_tool_execution",
    "extract_bee_citations_from_response",
]
