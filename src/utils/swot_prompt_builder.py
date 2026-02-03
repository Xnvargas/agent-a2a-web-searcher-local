"""
=============================================================================
SWOT PROMPT BUILDER - Dynamic System Prompt Generation
=============================================================================

Builds context-aware system prompts based on the current SWOT context.
The agent receives different instructions depending on what page the user is on.

=============================================================================
"""

from typing import Optional
from .swot_context import SWOTContextData


# Base capabilities - always included
BASE_SYSTEM_PROMPT = """You are a Solution Architect Assistant for IBM technology solutions.

CAPABILITIES:
- Search relevant documentation and past solutions
- Help draft solution architectures
- Answer questions about products, accounts, and opportunities
- Find similar past solutions for reference
- Query team coverage and expertise

GUIDELINES:
- Document searches automatically filter to the current context when applicable
- Cite your sources when referencing documents
- Be concise but thorough in your responses
- When creating solutions or artifacts, they will be linked to the current entity

Always be helpful, accurate, and transparent about your information sources."""


def build_swot_system_prompt(context: Optional[SWOTContextData]) -> str:
    """
    Build a dynamic system prompt based on SWOT context.

    Args:
        context: The current SWOT context (may be None for global mode)

    Returns:
        Complete system prompt string tailored to current scope
    """
    if not context:
        return BASE_SYSTEM_PROMPT + """

CURRENT MODE: Global
No specific entity is selected. Document searches are not filtered.
Help the user find what they're looking for across all data."""

    scope = context.scope
    summary = context.summary

    # Build context section based on scope type
    context_lines = ["\n\n" + "=" * 60, "CURRENT CONTEXT", "=" * 60]

    # -------------------------------------------------------------------------
    # OPPORTUNITY CONTEXT
    # -------------------------------------------------------------------------
    if scope.type == 'opportunity' and summary.entity_name:
        context_lines.append(f"""
MODE: Opportunity View
Opportunity: {summary.entity_name}
Account: {summary.account_name or 'Unknown'} ({summary.industry or 'Unknown industry'})
Status: {summary.status or 'Unknown'}""")

        if summary.use_case:
            # Truncate long use cases
            use_case_preview = summary.use_case[:500]
            if len(summary.use_case) > 500:
                use_case_preview += "..."
            context_lines.append(f"\nUse Case:\n{use_case_preview}")

        if summary.strategy:
            strategy_preview = summary.strategy[:300]
            if len(summary.strategy) > 300:
                strategy_preview += "..."
            context_lines.append(f"\nStrategy:\n{strategy_preview}")

        if summary.success_criteria:
            criteria_preview = summary.success_criteria[:300]
            if len(summary.success_criteria) > 300:
                criteria_preview += "..."
            context_lines.append(f"\nSuccess Criteria:\n{criteria_preview}")

        if summary.products:
            product_names = [p.get('name', 'Unknown') for p in summary.products]
            primary = [p.get('name') for p in summary.products if p.get('isPrimary')]
            products_str = ', '.join(product_names)
            if primary:
                products_str += f" (Primary: {', '.join(primary)})"
            context_lines.append(f"\nProducts in scope: {products_str}")

        if summary.contacts:
            contacts_str = ', '.join([
                f"{c.get('name', 'Unknown')} ({c.get('title', 'Unknown')})"
                for c in summary.contacts[:3]
            ])
            if len(summary.contacts) > 3:
                contacts_str += f" +{len(summary.contacts) - 3} more"
            context_lines.append(f"Key contacts: {contacts_str}")

        if summary.solution_overview:
            overview_preview = summary.solution_overview[:300]
            if len(summary.solution_overview) > 300:
                overview_preview += "..."
            context_lines.append(f"\nCurrent Solution Draft:\n{overview_preview}")

        context_lines.append(f"""
AUTOMATIC SCOPING:
- search_documents: Filters to this opportunity (ID: {scope.opportunity_id})
- find_similar_solutions: Excludes this opportunity from results
- create_solution_draft: Links to this opportunity
- create_document_artifact: Links to this opportunity and account
- get_technology_footprint: Uses this opportunity's account
- query_coverage: Uses this opportunity's account""")

    # -------------------------------------------------------------------------
    # ACCOUNT CONTEXT
    # -------------------------------------------------------------------------
    elif scope.type == 'account' and summary.entity_name:
        context_lines.append(f"""
MODE: Account View
Account: {summary.entity_name}
Industry: {summary.industry or 'Unknown'}
Segment: {summary.segment or 'Unknown'}""")

        if summary.technology_footprint:
            tech_names = [t.get('name', 'Unknown') for t in summary.technology_footprint]
            context_lines.append(f"\nExisting IBM technology: {', '.join(tech_names)}")

        if summary.team_members:
            team_str = ', '.join([
                f"{tm.get('name', 'Unknown')} ({tm.get('role', 'Unknown')})"
                for tm in summary.team_members[:5]
            ])
            if len(summary.team_members) > 5:
                team_str += f" +{len(summary.team_members) - 5} more"
            context_lines.append(f"Account team: {team_str}")

        context_lines.append(f"""
AUTOMATIC SCOPING:
- search_documents: Filters to this account (ID: {scope.account_id})
- get_technology_footprint: Uses this account
- query_coverage: Uses this account
- create_document_artifact: Links to this account""")

    # -------------------------------------------------------------------------
    # SOLUTION CONTEXT
    # -------------------------------------------------------------------------
    elif scope.type == 'solution':
        context_lines.append(f"""
MODE: Solution Editor
Editing solution for: {summary.entity_name or 'Unknown opportunity'}
Account: {summary.account_name or 'Unknown'}
Solution Status: {summary.solution_status or 'Unknown'}""")

        if summary.solution_overview:
            context_lines.append(f"\nCurrent Solution Overview:\n{summary.solution_overview[:500]}")

        context_lines.append(f"""
AUTOMATIC SCOPING:
- search_documents: Filters to parent opportunity
- find_similar_solutions: Find reference architectures
- Focus on helping refine and improve the solution""")

    # -------------------------------------------------------------------------
    # DASHBOARD CONTEXT
    # -------------------------------------------------------------------------
    elif scope.type == 'dashboard':
        context_lines.append("""
MODE: Dashboard
Overview of pipeline and recent activity.

AUTOMATIC SCOPING:
- Document searches are NOT filtered to any entity
- Help with pipeline overview and navigation
- Can help find specific opportunities or accounts""")

    # -------------------------------------------------------------------------
    # GLOBAL/DEFAULT CONTEXT
    # -------------------------------------------------------------------------
    else:
        context_lines.append("""
MODE: Global
No specific entity selected.

AUTOMATIC SCOPING:
- Document searches are NOT filtered
- Help the user find what they're looking for across all data
- Can navigate to specific entities""")

    return BASE_SYSTEM_PROMPT + '\n'.join(context_lines)
