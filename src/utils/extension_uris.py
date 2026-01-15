"""
=============================================================================
A2A EXTENSION URIs - Centralized Extension URI Constants
=============================================================================

This module provides centralized constants for all A2A extension URIs used
by the server and expected by the client (Carbon frontend).

USAGE:
------

```python
from utils.extension_uris import ExtensionURIs

# Use in metadata for messages
metadata = {
    ExtensionURIs.CITATION: {
        "citations": [...]
    }
}
```

PROTOCOL COMPLIANCE:
--------------------

These URIs follow the A2A extensions specification and are used by:
- Server: To emit structured metadata in message.metadata fields
- Client: To parse and render extension-specific UI components

EXTENSION CATEGORIES:
---------------------

UI Extensions (Server -> Client):
- Citation, Trajectory, Error, Form Request, Canvas, Agent Detail, OAuth, Settings

Service Extensions (Client -> Server):
- LLM, Embedding, MCP

=============================================================================
"""

from typing import Dict, Any, Optional, List


class ExtensionURIs:
    """
    All A2A extension URIs used by the server.

    These URIs are keyed in message metadata to communicate extension-specific
    data between the server and client.
    """

    # =========================================================================
    # UI Extensions (Server -> Client)
    # =========================================================================

    # Citation Extension - Source attribution for tool-based responses
    CITATION = "https://a2a-extensions.agentstack.beeai.dev/ui/citation/v1"

    # Trajectory Extension - Execution tracking and chain of thought
    TRAJECTORY = "https://a2a-extensions.agentstack.beeai.dev/ui/trajectory/v1"

    # Error Extension - Structured error reporting
    ERROR = "https://a2a-extensions.agentstack.beeai.dev/ui/error/v1"

    # Form Request Extension - Request user input during execution
    FORM_REQUEST = "https://a2a-extensions.agentstack.beeai.dev/ui/form-request/v1"

    # Canvas Extension - Artifact rendering and editing
    CANVAS = "https://a2a-extensions.agentstack.beeai.dev/ui/canvas/v1"

    # Agent Detail Extension - Agent metadata and capabilities
    AGENT_DETAIL = "https://a2a-extensions.agentstack.beeai.dev/ui/agent-detail/v1"

    # OAuth Extension - OAuth flow requests
    OAUTH_REQUEST = "https://a2a-extensions.agentstack.beeai.dev/ui/oauth/v1"

    # Settings Extension - User preference configuration
    SETTINGS = "https://a2a-extensions.agentstack.beeai.dev/ui/settings/v1"

    # =========================================================================
    # Service Extensions (Client -> Server)
    # =========================================================================

    # LLM Service Extension - External LLM configuration
    LLM = "https://a2a-extensions.agentstack.beeai.dev/services/llm/v1"

    # Embedding Service Extension - Embedding model configuration
    EMBEDDING = "https://a2a-extensions.agentstack.beeai.dev/services/embedding/v1"

    # MCP Service Extension - Model Context Protocol integration
    MCP = "https://a2a-extensions.agentstack.beeai.dev/services/mcp/v1"


def create_extension_metadata(uri: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create metadata dictionary keyed by extension URI.

    Args:
        uri: The extension URI from ExtensionURIs class
        data: The data to include under the URI key

    Returns:
        Dictionary with URI as key and data as value

    Example:
        ```python
        metadata = create_extension_metadata(
            ExtensionURIs.CITATION,
            {"citations": [...]}
        )
        # Returns: {"https://a2a-extensions.../citation/v1": {"citations": [...]}}
        ```
    """
    return {uri: data}


def merge_extension_metadata(*metadata_dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple extension metadata dictionaries.

    Args:
        *metadata_dicts: Variable number of metadata dictionaries to merge

    Returns:
        Single merged dictionary containing all extension metadata

    Example:
        ```python
        citation_meta = {ExtensionURIs.CITATION: {"citations": [...]}}
        trajectory_meta = {ExtensionURIs.TRAJECTORY: {"title": "...", "content": "..."}}
        merged = merge_extension_metadata(citation_meta, trajectory_meta)
        ```
    """
    result = {}
    for meta in metadata_dicts:
        result.update(meta)
    return result
