# A2A Content Metadata Guide

## Overview

This guide documents the content type metadata system added to enable visual differentiation in Carbon frontend (reasoning, tool calls, responses).

## Content Types

The server now emits trajectory metadata with structured `content_type` fields:

| Content Type | Description | When Emitted |
|--------------|-------------|--------------|
| `thinking` | Reasoning/thinking steps | Before any tool calls |
| `tool_call` | Tool invocation details | When LLM decides to use a tool |
| `tool_result` | Tool execution results | After tool completes |
| `response` | Final response text | After tool executions |
| `status` | Progress indicators | Status messages |

## Frontend Mapping

| Server `content_type` | Carbon UI Element |
|-----------------------|-------------------|
| `thinking` | `reasoning.steps` / `reasoning.content` |
| `tool_call` | `chain_of_thought` tool invocation card |
| `tool_result` | `chain_of_thought` result expansion |
| `response` | Main response text |
| `status` | Progress indicator / status badge |

## Trajectory Metadata Format

### Thinking Events

```json
{
  "title": "Thinking Step 1",
  "content": {
    "content": "Let me analyze the user's question...",
    "content_type": "thinking",
    "text_preview": "Let me analyze...",
    "step": 1
  }
}
```

### Tool Call Events

```json
{
  "title": "Tool Call: searx_search",
  "content": {
    "content_type": "tool_call",
    "tool_data": {
      "type": "tool_call",
      "tool_name": "searx_search",
      "args": {"query": "latest AI news"},
      "tool_call_id": "call_abc123",
      "status": "in_progress"
    }
  }
}
```

### Tool Result Events

```json
{
  "title": "Tool Result: searx_search",
  "content": {
    "content_type": "tool_result",
    "tool_data": {
      "type": "tool_result",
      "tool_name": "searx_search",
      "result_preview": "{\"results\": [{\"title\": \"...\"}...]}",
      "result_length": 2500,
      "tool_call_id": "call_abc123",
      "status": "success"
    }
  }
}
```

## Implementation Files

- **`src/utils/content_parts.py`** - Helper functions and constants
- **`src/agentstack_agents/agent.py`** - Streaming handler with content categorization

## Helper Functions

```python
from utils.content_parts import (
    ContentType,
    format_thinking_trajectory,
    format_tool_call_trajectory,
    format_tool_result_trajectory,
)

# Create thinking metadata
title, content = format_thinking_trajectory(
    content="Analyzing the query...",
    step_number=1
)

# Create tool call metadata
title, content = format_tool_call_trajectory(
    tool_name="searx_search",
    args={"query": "test"},
    tool_call_id="call_123"
)

# Create tool result metadata
title, content = format_tool_result_trajectory(
    tool_name="searx_search",
    result={"results": [...]},
    tool_call_id="call_123",
    status="success"
)
```

## Content Categorization Logic

Content is categorized based on position relative to tool calls:

```
[User Message]
    ↓
[LLM Response Before Tools] → content_type: "thinking"
    ↓
[Tool Call] → content_type: "tool_call"
    ↓
[Tool Execution]
    ↓
[Tool Result] → content_type: "tool_result"
    ↓
[LLM Response After Tools] → content_type: "response"
```

## Protocol Compliance

This implementation uses the standard A2A protocol mechanisms:

1. **Trajectory Extension** - Used to emit metadata via `trajectory.trajectory_metadata()`
2. **JSON Content** - Metadata is serialized as JSON in the content field
3. **No Protocol Breaks** - Uses existing A2A primitives, no custom event types

## Testing

To verify the metadata is being emitted correctly:

```python
# Run the agent and observe trajectory metadata in logs
# Look for entries with "Thinking Step", "Tool Call:", "Tool Result:"
```

The metadata will appear in the BeeAI UI trajectory panel, and can be consumed by the Carbon frontend to render appropriate UI elements.
