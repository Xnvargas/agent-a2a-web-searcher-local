"""Handoff tool: delegate to the Document Agent."""

from tools.langchain.base import LangChainTool
from langchain_core.tools import tool


class HandoffToDocumentTool(LangChainTool):
    name = "handoff_to_document"
    description = (
        "Delegate a question to the Document Agent. Use for document search, "
        "finding docs about a topic, or retrieving full document content."
    )

    def get_schema(self):
        return {
            "user_message": {
                "type": "string",
                "required": True,
                "description": "The question or search request to delegate to the Document Agent.",
            }
        }

    async def execute(self, user_message: str) -> str:
        from agents.base import create_specialist_agent, MODEL_REASONING
        from agents.prompts.document_prompt import build_document_prompt
        from agents.tool_sets import get_document_tools
        from agents.history import build_specialist_briefing
        from utils.swot_context import SWOTContext
        from langchain_core.messages import HumanMessage

        ctx = SWOTContext.get_current()
        ctx_dict = _context_to_dict(ctx)

        prompt = build_document_prompt(ctx_dict)
        doc_tools = get_document_tools()

        agent = create_specialist_agent(
            agent_name="document",
            tools=doc_tools,
            system_prompt=prompt,
            model=MODEL_REASONING,
            recursion_limit=10,
        )

        briefing = build_specialist_briefing(ctx_dict, user_message)
        messages = [HumanMessage(content=f"{briefing}\n\nUser question: {user_message}")]

        result = await agent.ainvoke(
            {"messages": messages, "llm_calls": 0, "tool_instances": {t.name: t for t in doc_tools}, "tool_attempts": {}}
        )

        return _extract_final_response(result["messages"])

    def get_langchain_tool(self):
        @tool
        def handoff_to_document(user_message: str) -> str:
            """Delegate a question to the Document Agent for document search and retrieval."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return handoff_to_document


def _context_to_dict(ctx) -> dict:
    if not ctx:
        return {}
    return {
        "scope": ctx.scope.get_filter_dict() | {"type": ctx.scope.type},
        "summary": {"entityName": ctx.summary.entity_name},
    }


def _extract_final_response(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai" and msg.content:
            return str(msg.content)
    return "No response from specialist agent."
