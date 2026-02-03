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
- A2A Parts: DataPart helpers for Carbon AI Chat compatibility

DOCUMENTATION REFERENCES:
-------------------------
- AgentStack messages: https://raw.githubusercontent.com/i-am-bee/agentstack/main/docs/stable/agent-integration/messages.mdx
- AgentStack trajectory: https://raw.githubusercontent.com/i-am-bee/agentstack/main/docs/stable/agent-integration/trajectory.mdx
- Carbon AI Chat: https://github.com/carbon-design-system/carbon-ai-chat

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
    create_trajectory_metadata,
    # NEW: A2A DataPart helpers for Carbon AI Chat
    emit_tool_call_with_trajectory,
    emit_tool_result_with_trajectory,
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
# SWOT Context Management
# -----------------------------------------------------------------------------
from .swot_context import (
    SWOTContext,
    SWOTContextData,
    SWOTScope,
    SWOTContextSummary,
    extract_swot_context,
)

from .swot_prompt_builder import build_swot_system_prompt

# -----------------------------------------------------------------------------
# A2A Parts - DataPart helpers for Carbon AI Chat compatibility
# -----------------------------------------------------------------------------
from .a2a_parts import (
    # Content type constants
    A2AContentType,
    # DataPart creators
    create_tool_call_data_part,
    create_tool_result_data_part,
    create_thinking_text_part,
    create_response_text_part,
    # AgentMessage helpers
    create_tool_call_agent_message,
    create_tool_result_agent_message,
    # Dual-emit helpers (trajectory + DataPart)
    emit_tool_call_with_trajectory,
    emit_tool_result_with_trajectory,
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

    # A2A Parts - DataPart helpers (Carbon AI Chat compatibility)
    "A2AContentType",
    "create_tool_call_data_part",
    "create_tool_result_data_part",
    "create_thinking_text_part",
    "create_response_text_part",
    "create_tool_call_agent_message",
    "create_tool_result_agent_message",
    "emit_tool_call_with_trajectory",
    "emit_tool_result_with_trajectory",

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

    # SWOT Context Management
    "SWOTContext",
    "SWOTContextData",
    "SWOTScope",
    "SWOTContextSummary",
    "extract_swot_context",
    "build_swot_system_prompt",
]
