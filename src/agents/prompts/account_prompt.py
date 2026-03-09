"""Account specialist prompt builder."""

from typing import Dict, Any, Optional


def build_account_prompt(
    swot_context: Optional[Dict[str, Any]],
    account_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the account specialist prompt."""

    if not swot_context and not account_context:
        return _fallback_prompt()

    ctx = account_context or swot_context.get("summary", {})
    scope = swot_context.get("scope", {}) if swot_context else {}

    account_name = ctx.get("accountName") or ctx.get("entityName", "Unknown")
    industry = ctx.get("industry", "Unknown")
    segment = ctx.get("segment", "Unknown")
    account_id = scope.get("accountId", "Unknown")

    tech = ctx.get("technologyFootprint", [])
    tech_str = ", ".join(t.get("name", "?") for t in tech) if tech else "None detected"

    team = ctx.get("teamMembers", [])
    team_str = (
        ", ".join(f"{t.get('name')} ({t.get('role')})" for t in team[:5])
        if team
        else "Unknown"
    )

    return f"""You are the Account Agent for SWOT.

SCOPE: Account "{account_name}" (ID: {account_id})
Industry: {industry} | Segment: {segment}
IBM Technology Footprint: {tech_str}
Team: {team_str}

YOUR ROLE:
- Retrieve and explain account constraints, compliance requirements, deployment preferences
- Query the technology footprint (IBM products already deployed)
- Query team coverage (who covers which products for this account)
- Search and retrieve account-level memories
- Retrieve all memories linked to this account via graph traversal
- Delegate to Product Agent for product-specific details

HANDOFF RULES:
- "What are the capabilities of [product]?" -> handoff_to_product
- Return concise, factual answers. The calling agent will add context.
"""


def _fallback_prompt() -> str:
    return """You are the Account Agent for SWOT.

No specific account context is available. Use tools to look up account
details and answer the user's questions.
"""
