"""Handoff tool: delegate to the Product Agent."""

from tools.langchain.base import LangChainTool
from langchain_core.tools import tool


class HandoffToProductTool(LangChainTool):
    name = "handoff_to_product"
    description = (
        "Delegate a question to the Product Agent. Use for questions about "
        "product capabilities, features, documentation, deployment options, "
        "or technical details."
    )

    def get_schema(self):
        return {
            "user_message": {
                "type": "string",
                "required": True,
                "description": "The question to delegate to the Product Agent. Pass verbatim.",
            }
        }

    async def execute(self, user_message: str) -> str:
        from agents.base import create_specialist_agent, MODEL_REASONING
        from agents.prompts.product_prompt import build_product_prompt
        from agents.tool_sets import get_product_tools
        from agents.history import build_specialist_briefing
        from utils.swot_context import SWOTContext
        from langchain_core.messages import HumanMessage

        ctx = SWOTContext.get_current()
        ctx_dict = _context_to_dict(ctx)

        prompt = build_product_prompt(ctx_dict)
        product_tools = get_product_tools()

        agent = create_specialist_agent(
            agent_name="product",
            tools=product_tools,
            system_prompt=prompt,
            model=MODEL_REASONING,
            recursion_limit=10,
        )

        briefing = build_specialist_briefing(ctx_dict, user_message)
        messages = [HumanMessage(content=f"{briefing}\n\nUser question: {user_message}")]

        result = await agent.ainvoke(
            {"messages": messages, "llm_calls": 0, "tool_instances": {t.name: t for t in product_tools}, "tool_attempts": {}}
        )

        return _extract_final_response(result["messages"])

    def get_langchain_tool(self):
        @tool
        def handoff_to_product(user_message: str) -> str:
            """Delegate a question to the Product Agent for product-level details."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return handoff_to_product


def _context_to_dict(ctx) -> dict:
    if not ctx:
        return {}
    return {
        "scope": ctx.scope.get_filter_dict() | {"type": ctx.scope.type},
        "summary": {
            "entityName": ctx.summary.entity_name,
            "products": ctx.summary.products or [],
        },
    }


def _extract_final_response(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            return str(msg.content)
    return "No response from specialist agent."
