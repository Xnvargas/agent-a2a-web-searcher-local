"""Handoff tool: delegate to the Opportunity Agent."""

from tools.langchain.base import LangChainTool
from langchain_core.tools import tool


class HandoffToOpportunityTool(LangChainTool):
    name = "handoff_to_opportunity"
    description = (
        "Delegate a question to the Opportunity Agent. Use for questions about "
        "opportunity status, strategy, contacts, products in scope, use case, "
        "or similar past solutions."
    )

    def get_schema(self):
        return {
            "user_message": {
                "type": "string",
                "required": True,
                "description": "The user's question to delegate to the Opportunity Agent. Pass verbatim.",
            }
        }

    async def execute(self, user_message: str) -> str:
        from agents.base import create_specialist_agent, MODEL_REASONING
        from agents.prompts.opportunity_prompt import build_opportunity_prompt
        from agents.tool_sets import get_opportunity_tools
        from agents.history import build_specialist_briefing
        from utils.swot_context import SWOTContext
        from langchain_core.messages import HumanMessage

        ctx = SWOTContext.get_current()
        ctx_dict = _context_to_dict(ctx)

        prompt = build_opportunity_prompt(ctx_dict)
        opp_tools = get_opportunity_tools()

        agent = create_specialist_agent(
            agent_name="opportunity",
            tools=opp_tools,
            system_prompt=prompt,
            model=MODEL_REASONING,
            recursion_limit=15,
        )

        from utils.conversation_context import ConversationContext
        conversation_summary = ConversationContext.get_summary()
        briefing = build_specialist_briefing(ctx_dict, user_message, conversation_summary=conversation_summary)
        messages = [HumanMessage(content=f"{briefing}\n\nUser question: {user_message}")]

        from ._utils import run_specialist
        return await run_specialist(
            agent, messages, {t.name: t for t in opp_tools}, "opportunity",
            recursion_limit=15,
        )

    def get_langchain_tool(self):
        @tool
        def handoff_to_opportunity(user_message: str) -> str:
            """Delegate a question to the Opportunity Agent for opportunity-level details."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return handoff_to_opportunity


def _context_to_dict(ctx) -> dict:
    """Convert SWOTContextData to a plain dict for prompt builders."""
    if not ctx:
        return {}
    return {
        "scope": ctx.scope.get_filter_dict() | {"type": ctx.scope.type},
        "summary": {
            "entityName": ctx.summary.entity_name,
            "accountName": ctx.summary.account_name,
            "industry": ctx.summary.industry,
            "status": ctx.summary.status,
            "useCase": ctx.summary.use_case,
            "strategy": ctx.summary.strategy,
            "products": ctx.summary.products or [],
            "contacts": ctx.summary.contacts or [],
            "technologyFootprint": ctx.summary.technology_footprint or [],
            "teamMembers": ctx.summary.team_members or [],
            "segment": ctx.summary.segment,
            "solutionOverview": ctx.summary.solution_overview,
            "solutionStatus": ctx.summary.solution_status,
        },
    }


