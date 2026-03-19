"""Handoff tool: delegate to the Architect Agent."""

from tools.langchain.base import LangChainTool
from langchain_core.tools import tool


class HandoffToArchitectTool(LangChainTool):
    name = "handoff_to_architect"
    description = (
        "Delegate to the Architect Agent. Use for creating, updating, or "
        "iterating on solution architectures, generating diagrams, or "
        "managing architecture workflows."
    )

    def get_schema(self):
        return {
            "user_message": {
                "type": "string",
                "required": True,
                "description": "The architecture request to delegate to the Architect Agent.",
            }
        }

    async def execute(self, user_message: str) -> str:
        from agents.base import create_specialist_agent, MODEL_REASONING
        from agents.prompts.architect_prompt import build_architect_prompt
        from agents.tool_sets import get_architect_tools
        from agents.history import build_specialist_briefing
        from utils.swot_context import SWOTContext
        from langchain_core.messages import HumanMessage

        ctx = SWOTContext.get_current()
        ctx_dict = _context_to_dict(ctx)

        prompt = build_architect_prompt(ctx_dict)
        arch_tools = get_architect_tools()

        agent = create_specialist_agent(
            agent_name="architect",
            tools=arch_tools,
            system_prompt=prompt,
            model=MODEL_REASONING,
            recursion_limit=20,
        )

        briefing = build_specialist_briefing(ctx_dict, user_message)
        messages = [HumanMessage(content=f"{briefing}\n\nUser question: {user_message}")]

        from ._utils import run_specialist
        return await run_specialist(
            agent, messages, {t.name: t for t in arch_tools}, "architect"
        )

    def get_langchain_tool(self):
        @tool
        def handoff_to_architect(user_message: str) -> str:
            """Delegate to the Architect Agent for solution architecture work."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return handoff_to_architect


def _context_to_dict(ctx) -> dict:
    if not ctx:
        return {}
    return {
        "scope": ctx.scope.get_filter_dict() | {"type": ctx.scope.type, "solutionId": ctx.scope.solution_id},
        "summary": {
            "entityName": ctx.summary.entity_name,
            "accountName": ctx.summary.account_name,
            "useCase": ctx.summary.use_case,
            "products": ctx.summary.products or [],
            "solutionOverview": ctx.summary.solution_overview,
            "solutionStatus": ctx.summary.solution_status,
        },
    }


