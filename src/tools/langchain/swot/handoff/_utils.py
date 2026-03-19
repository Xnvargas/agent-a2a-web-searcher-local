"""Shared utilities for handoff tools."""

import traceback


def extract_final_response(messages: list) -> str:
    """
    Extract the final AI response from a specialist agent's message list.

    Handles edge cases:
    - Normal case: last AI message with content
    - Recursion limit: last message may be a ToolMessage; find last AI with content
    - Empty content: AI message exists but content is empty (tool-call-only message)
    - No messages: agent produced no output
    """
    if not messages:
        return "No response from specialist agent (empty message list)."

    # Walk backwards looking for the last AI message with substantive content
    for msg in reversed(messages):
        if not hasattr(msg, "type"):
            continue
        if msg.type == "ai" and msg.content and msg.content.strip():
            # Skip AI messages that only contain tool call XML fragments
            content = str(msg.content).strip()
            if content.startswith("<tool_call") or content.startswith("<function="):
                continue
            return content

    # Fallback: check if the last message is a ToolMessage with useful content
    last = messages[-1]
    if hasattr(last, "type") and last.type == "tool" and last.content:
        return (
            f"[Specialist agent did not produce a final response. "
            f"Last tool result: {str(last.content)[:2000]}]"
        )

    return "No response from specialist agent."


async def run_specialist(agent, messages: list, tool_instances: dict, agent_name: str, recursion_limit: int = 25) -> str:
    """
    Invoke a specialist agent with error handling.

    Returns the specialist's final response text, or a structured error message.
    """
    try:
        result = await agent.ainvoke(
            {"messages": messages, "llm_calls": 0, "tool_instances": tool_instances, "tool_attempts": {}},
            config={"recursion_limit": recursion_limit},
        )
        return extract_final_response(result["messages"])
    except Exception as e:
        error_type = type(e).__name__
        error_brief = str(e)[:500]
        tb = traceback.format_exc()
        print(f"  ERROR in {agent_name} specialist: {error_type}: {error_brief}")
        print(tb)
        return f"Error in {agent_name} agent ({error_type}): {error_brief}"
