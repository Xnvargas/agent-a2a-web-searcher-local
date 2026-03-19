"""
Conversation context propagation via ContextVar.

Allows the orchestrator's conversation summary to reach specialist agents
through handoff tools without modifying the LLM tool call interface.
"""

from contextvars import ContextVar
from typing import Optional


_conversation_summary: ContextVar[Optional[str]] = ContextVar(
    "conversation_summary", default=None
)


class ConversationContext:
    """Thread-safe conversation summary propagation."""

    @staticmethod
    def set_summary(summary: Optional[str]) -> None:
        _conversation_summary.set(summary)

    @staticmethod
    def get_summary() -> Optional[str]:
        return _conversation_summary.get()
