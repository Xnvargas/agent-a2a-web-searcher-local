"""
Tool partitioning for multi-agent architecture.

Each function returns the filtered tool list for one specialist.
Tools are resolved by name from the existing ToolRegistry.
"""

from typing import List


def get_orchestrator_tools() -> List:
    """Orchestrator only has handoff tools -- no domain tools."""
    from tools.langchain.swot.handoff import (
        HandoffToOpportunityTool,
        HandoffToAccountTool,
        HandoffToProductTool,
        HandoffToDocumentTool,
        HandoffToResearchTool,
        HandoffToArchitectTool,
    )
    return [
        HandoffToOpportunityTool(),
        HandoffToAccountTool(),
        HandoffToProductTool(),
        HandoffToDocumentTool(),
        HandoffToResearchTool(),
        HandoffToArchitectTool(),
    ]


def get_opportunity_tools() -> List:
    """Opp agent: context + entities + similar solutions + memory + 2 handoffs."""
    from tools import get_tool_by_name
    from tools.langchain.swot.handoff import HandoffToAccountTool, HandoffToProductTool

    tools = []
    for name in [
        "get_current_context",
        "query_entities",
        "get_entity_details",
        "find_similar_solutions",
        "search_memory",
        "add_memory",
    ]:
        t = get_tool_by_name(name)
        if t:
            tools.append(t)

    tools.append(HandoffToAccountTool())
    tools.append(HandoffToProductTool())
    return tools


def get_account_tools() -> List:
    """Account agent: entity details + tech + coverage + memory."""
    from tools import get_tool_by_name
    from tools.langchain.swot.handoff import HandoffToProductTool

    tools = []
    for name in [
        "get_entity_details",
        "get_technology_footprint",
        "query_coverage",
        "search_memory",
        "get_entity_memory",
    ]:
        t = get_tool_by_name(name)
        if t:
            tools.append(t)

    tools.append(HandoffToProductTool())
    return tools


def get_product_tools() -> List:
    """Product agent: entity details + entities + docs + memory."""
    from tools import get_tool_by_name
    from tools.langchain.swot.handoff import HandoffToDocumentTool

    tools = []
    for name in [
        "get_entity_details",
        "query_entities",
        "search_documents",
        "search_memory",
    ]:
        t = get_tool_by_name(name)
        if t:
            tools.append(t)

    tools.append(HandoffToDocumentTool())
    return tools


def get_document_tools() -> List:
    """Document agent (leaf): search + full text + entity lookup."""
    from tools import get_tool_by_name

    tools = []
    for name in ["search_documents", "get_document_text", "query_entities"]:
        t = get_tool_by_name(name)
        if t:
            tools.append(t)
    return tools


def get_research_tools() -> List:
    """Research agent: web search + scraping."""
    from tools import get_tool_by_name

    tools = []
    for name in ["tavily_search", "firecrawl_scrape"]:
        t = get_tool_by_name(name)
        if t:
            tools.append(t)
    return tools


def get_architect_tools() -> List:
    """Architect agent: solution CRUD + search + similar."""
    from tools import get_tool_by_name

    tools = []
    for name in [
        "get_solution_content",
        "create_solution_draft",
        "update_solution",
        "search_documents",
        "find_similar_solutions",
    ]:
        t = get_tool_by_name(name)
        if t:
            tools.append(t)
    return tools
