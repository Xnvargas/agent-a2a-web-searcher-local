"""Handoff tool: delegate to the Account Agent."""

from tools.langchain.base import LangChainTool
from langchain_core.tools import tool


class HandoffToAccountTool(LangChainTool):
    name = "handoff_to_account"
    description = (
        "Delegate a question to the Account Agent. Use for questions about "
        "account constraints, compliance, technology footprint, team coverage, "
        "or account-level details."
    )

    def get_schema(self):
        return {
            "user_message": {
                "type": "string",
                "required": True,
                "description": "The question to delegate to the Account Agent. Pass verbatim.",
            }
        }

    async def execute(self, user_message: str) -> str:
        from agents.base import create_specialist_agent, MODEL_REASONING
        from agents.prompts.account_prompt import build_account_prompt
        from agents.tool_sets import get_account_tools
        from agents.history import build_specialist_briefing
        from utils.swot_context import SWOTContext
        from langchain_core.messages import HumanMessage

        ctx = SWOTContext.get_current()
        ctx_dict = _context_to_dict(ctx)

        prompt = build_account_prompt(ctx_dict)
        account_tools = get_account_tools()

        agent = create_specialist_agent(
            agent_name="account",
            tools=account_tools,
            system_prompt=prompt,
            model=MODEL_REASONING,
            recursion_limit=10,
        )

        briefing = build_specialist_briefing(ctx_dict, user_message)
        messages = [HumanMessage(content=f"{briefing}\n\nUser question: {user_message}")]

        from ._utils import run_specialist
        return await run_specialist(
            agent, messages, {t.name: t for t in account_tools}, "account"
        )

    def get_langchain_tool(self):
        @tool
        def handoff_to_account(user_message: str) -> str:
            """Delegate a question to the Account Agent for account-level details."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return handoff_to_account


def _context_to_dict(ctx) -> dict:
    if not ctx:
        return {}
    return {
        "scope": ctx.scope.get_filter_dict() | {"type": ctx.scope.type},
        "summary": {
            "entityName": ctx.summary.entity_name,
            "accountName": ctx.summary.account_name,
            "industry": ctx.summary.industry,
            "segment": ctx.summary.segment,
            "technologyFootprint": ctx.summary.technology_footprint or [],
            "teamMembers": ctx.summary.team_members or [],
        },
    }


