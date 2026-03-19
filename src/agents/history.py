"""
Conversation history management for the orchestrator.

Strategy:
- Maintain full recent history up to a dynamic token budget
- When history exceeds budget, summarize older turns into a compact prefix
- Specialists receive ONLY the current task + a brief context sentence

Token budget: Approximately 8000 tokens for history
  (leaving ~42000 for system prompt + tool schemas + current turn + response)
"""

from typing import Optional, Tuple, List, Dict, Any


HISTORY_TOKEN_BUDGET = 8000
CHARS_PER_TOKEN_ESTIMATE = 4  # Conservative estimate for English text


def estimate_tokens(text: str) -> int:
    """Approximate token count using character-based estimate."""
    return len(text) // CHARS_PER_TOKEN_ESTIMATE


def apply_sliding_window(
    messages: list,
    existing_summary: Optional[str] = None,
    token_budget: int = HISTORY_TOKEN_BUDGET,
) -> Tuple[list, Optional[str], bool]:
    """
    Apply sliding window to conversation history.

    Returns:
        (windowed_messages, updated_summary, needs_summarization)

    If needs_summarization is True, the caller should invoke the LLM
    to summarize the dropped turns and store the result.
    """
    total_tokens = sum(estimate_tokens(str(getattr(m, "content", str(m)))) for m in messages)

    if total_tokens <= token_budget:
        return messages, existing_summary, False

    # Find the cut point: keep as many recent turns as fit in budget
    kept = []
    running_tokens = 0
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(str(getattr(msg, "content", str(msg))))
        if running_tokens + msg_tokens > token_budget:
            break
        kept.insert(0, msg)
        running_tokens += msg_tokens

    # Build a lightweight summary of dropped turns so context isn't silently lost
    dropped_count = len(messages) - len(kept)
    if dropped_count > 0:
        dropped = messages[:dropped_count]
        # Extract key info from dropped messages for a compact summary
        user_topics = []
        for msg in dropped:
            role = getattr(msg, "type", None) or getattr(msg, "role", None)
            if role in ("human", "user"):
                content = str(getattr(msg, "content", ""))[:150]
                if content:
                    user_topics.append(content)

        summary_parts = []
        if existing_summary:
            summary_parts.append(existing_summary)
        topic_preview = "; ".join(user_topics[:3])
        summary_parts.append(
            f"[{dropped_count} earlier messages dropped from context. "
            f"User topics covered: {topic_preview or 'N/A'}]"
        )
        updated_summary = " ".join(summary_parts)
        return kept, updated_summary, True

    return kept, existing_summary, False


def build_specialist_briefing(
    swot_context: Optional[Dict[str, Any]],
    user_message: str,
    conversation_summary: Optional[str] = None,
) -> str:
    """
    Build a 2-3 sentence briefing for a specialist agent.

    This replaces passing the full history. Specialists get:
    - What entity the user is working with
    - What the conversation has been about (if relevant)
    - The specific question to answer
    """
    if not swot_context:
        briefing = "User is working in global scope."
    else:
        summary = swot_context.get("summary", {})
        scope = swot_context.get("scope", {})

        entity = summary.get("entityName", "Unknown")
        account = summary.get("accountName", "")
        scope_type = scope.get("type", "global")

        briefing = f"User is working in {scope_type} scope"
        if entity:
            briefing += f" on '{entity}'"
        if account:
            briefing += f" (account: {account})"
        briefing += "."

    if conversation_summary:
        briefing += f" Previous discussion context: {conversation_summary[:200]}"

    return briefing


def get_last_user_message(messages: list) -> str:
    """Extract the last user message content from a message list."""
    for msg in reversed(messages):
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        if role in ("human", "user"):
            return str(getattr(msg, "content", str(msg)))
    return ""
