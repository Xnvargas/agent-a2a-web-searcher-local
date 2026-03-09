"""
Architect Agent — Stateful, TODO-driven solution architecture workflow.

Internal graph:
  plan -> research -> write -> [next_todo | done] -> END

State persists across turns via:
- solutions.section_metadata (which sections are done)
- solutions.architecture_details (the actual draft content)

This module provides the architect node function used by the orchestrator,
as well as the internal architect sub-graph for TODO-driven workflows.
"""

from typing import Optional, Dict, Any, List
import operator

from typing_extensions import TypedDict, Annotated


class ArchitectInternalState(TypedDict):
    """Internal state for the architect's TODO-driven workflow."""
    messages: Annotated[list, operator.add]
    solution_id: Optional[str]
    opportunity_id: Optional[str]

    # TODO tracking
    todos: List[dict]
    current_todo_index: int
    phase: str  # 'planning' | 'researching' | 'writing' | 'refining' | 'awaiting_user'

    # Draft accumulation
    current_section_draft: str

    # Tool state
    llm_calls: int
    tool_instances: dict


async def run_architect_workflow(
    swot_context: Dict[str, Any],
    user_message: str,
    api_base: str = "http://192.168.0.58:11434",
) -> str:
    """
    Run the architect agent as a standalone sub-graph invocation.

    For now, this delegates to the simple specialist pattern (same as handoff tools).
    The TODO-driven workflow with plan/research/write phases will be implemented
    in a future iteration once the base multi-agent routing is validated.

    Args:
        swot_context: The SWOT context dict
        user_message: The user's architecture request
        api_base: Ollama server URL

    Returns:
        The architect's response text
    """
    from agents.base import create_specialist_agent, MODEL_REASONING
    from agents.prompts.architect_prompt import build_architect_prompt
    from agents.tool_sets import get_architect_tools
    from agents.history import build_specialist_briefing
    from langchain_core.messages import HumanMessage

    prompt = build_architect_prompt(swot_context)
    arch_tools = get_architect_tools()

    agent = create_specialist_agent(
        agent_name="architect",
        tools=arch_tools,
        system_prompt=prompt,
        model=MODEL_REASONING,
        api_base=api_base,
        recursion_limit=20,
    )

    briefing = build_specialist_briefing(swot_context, user_message)
    messages = [HumanMessage(content=f"{briefing}\n\nUser request: {user_message}")]

    result = await agent.ainvoke(
        {
            "messages": messages,
            "llm_calls": 0,
            "tool_instances": {t.name: t for t in arch_tools},
            "tool_attempts": {},
        }
    )

    # Extract final response
    for msg in reversed(result["messages"]):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            return str(msg.content)

    return "No response from architect agent."
