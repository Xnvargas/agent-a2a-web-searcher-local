"""
=============================================================================
SWOT CONTEXT - Context Management for SWOT Agent Tools
=============================================================================

Provides async-safe context storage that tools can access to automatically
scope their queries to the current entity (opportunity, account, etc.).

USAGE IN AGENT HANDLER:
-----------------------
```python
from utils.swot_context import SWOTContext, extract_swot_context

extensions = context.request.params.get('extensions', {})
swot_ctx = extract_swot_context(extensions)
SWOTContext.set_current(swot_ctx)
```

USAGE IN TOOLS:
---------------
```python
from utils.swot_context import SWOTContext

filters = SWOTContext.get_filters()
# Returns: {'opportunityId': '...', 'accountId': '...'} or {}
```

=============================================================================
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from contextvars import ContextVar


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SWOTScope:
    """
    Scope identifies WHERE in the app the user is.
    Tools use this to automatically filter queries.
    """
    type: str = "global"  # 'global', 'opportunity', 'account', 'solution', 'dashboard'
    opportunity_id: Optional[str] = None
    account_id: Optional[str] = None
    solution_id: Optional[str] = None
    product_ids: Optional[List[str]] = None

    def has_opportunity_scope(self) -> bool:
        """Check if we have opportunity-level scope."""
        return self.type in ('opportunity', 'solution') and self.opportunity_id is not None

    def has_account_scope(self) -> bool:
        """Check if we have account-level scope."""
        return self.type in ('opportunity', 'account', 'solution') and self.account_id is not None

    def get_filter_dict(self) -> Dict[str, Any]:
        """
        Get filters for API calls based on scope.
        Keys match the SWOT API parameter names.
        """
        filters = {}
        if self.opportunity_id:
            filters['opportunityId'] = self.opportunity_id
        if self.account_id:
            filters['accountId'] = self.account_id
        if self.solution_id:
            filters['solutionId'] = self.solution_id
        if self.product_ids:
            filters['productIds'] = self.product_ids
        return filters


@dataclass
class SWOTContextSummary:
    """
    Human-readable summary for system prompt.
    This is what the agent "knows" about the current view.
    """
    # Primary entity
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None

    # Opportunity fields
    use_case: Optional[str] = None
    strategy: Optional[str] = None
    success_criteria: Optional[str] = None
    status: Optional[str] = None
    classification: Optional[str] = None

    # Account fields
    account_name: Optional[str] = None
    industry: Optional[str] = None
    segment: Optional[str] = None

    # Solution fields
    solution_overview: Optional[str] = None
    solution_status: Optional[str] = None

    # Relationships (lists of dicts)
    products: Optional[List[Dict[str, Any]]] = None
    contacts: Optional[List[Dict[str, Any]]] = None
    technology_footprint: Optional[List[Dict[str, Any]]] = None
    team_members: Optional[List[Dict[str, Any]]] = None


@dataclass
class SWOTContextData:
    """Full context from frontend via A2A extensions."""
    scope: SWOTScope = field(default_factory=SWOTScope)
    summary: SWOTContextSummary = field(default_factory=SWOTContextSummary)
    fetched_at: Optional[str] = None


# =============================================================================
# CONTEXT EXTRACTION FROM A2A
# =============================================================================

def extract_swot_context(extensions: Optional[Dict[str, Any]]) -> Optional[SWOTContextData]:
    """
    Extract SWOTContextData from A2A extensions.

    Args:
        extensions: The extensions dict from A2A request params
                   Expected structure: extensions.context = { scope: {...}, summary: {...} }

    Returns:
        SWOTContextData if context present, None otherwise
    """
    if not extensions:
        return None

    ctx_data = extensions.get('context')
    if not ctx_data:
        return None

    # Parse scope (camelCase from frontend → snake_case for Python)
    scope_data = ctx_data.get('scope', {})
    scope = SWOTScope(
        type=scope_data.get('type', 'global'),
        opportunity_id=scope_data.get('opportunityId'),
        account_id=scope_data.get('accountId'),
        solution_id=scope_data.get('solutionId'),
        product_ids=scope_data.get('productIds')
    )

    # Parse summary
    summary_data = ctx_data.get('summary', {})
    summary = SWOTContextSummary(
        entity_name=summary_data.get('entityName'),
        entity_type=summary_data.get('entityType'),
        use_case=summary_data.get('useCase'),
        strategy=summary_data.get('strategy'),
        success_criteria=summary_data.get('successCriteria'),
        status=summary_data.get('status'),
        classification=summary_data.get('classification'),
        account_name=summary_data.get('accountName'),
        industry=summary_data.get('industry'),
        segment=summary_data.get('segment'),
        solution_overview=summary_data.get('solutionOverview'),
        solution_status=summary_data.get('solutionStatus'),
        products=summary_data.get('products'),
        contacts=summary_data.get('contacts'),
        technology_footprint=summary_data.get('technologyFootprint'),
        team_members=summary_data.get('teamMembers')
    )

    return SWOTContextData(
        scope=scope,
        summary=summary,
        fetched_at=ctx_data.get('fetchedAt')
    )


# =============================================================================
# CONTEXT MANAGER (Thread/Async Safe via ContextVar)
# =============================================================================

# ContextVar ensures each async task has isolated context
_current_context: ContextVar[Optional[SWOTContextData]] = ContextVar(
    'swot_context',
    default=None
)


class SWOTContext:
    """
    Static class for managing SWOT context across tools.

    Uses ContextVar for async-safety - each async task gets its own context.
    Set once at the start of request handling, read by any tool during execution.
    """

    @staticmethod
    def set_current(ctx: Optional[SWOTContextData]) -> None:
        """Set the current SWOT context for this async task."""
        _current_context.set(ctx)

    @staticmethod
    def get_current() -> Optional[SWOTContextData]:
        """Get the current SWOT context."""
        return _current_context.get()

    @staticmethod
    def get_scope() -> Optional[SWOTScope]:
        """Get just the scope from current context."""
        ctx = _current_context.get()
        return ctx.scope if ctx else None

    @staticmethod
    def get_summary() -> Optional[SWOTContextSummary]:
        """Get just the summary from current context."""
        ctx = _current_context.get()
        return ctx.summary if ctx else None

    @staticmethod
    def get_filters() -> Dict[str, Any]:
        """
        Get scope filters for API calls.

        Returns dict with keys matching SWOT API parameters:
        - opportunityId
        - accountId
        - solutionId
        - productIds

        Returns empty dict if no context or global scope.
        """
        ctx = _current_context.get()
        if ctx and ctx.scope:
            return ctx.scope.get_filter_dict()
        return {}

    @staticmethod
    def get_opportunity_id() -> Optional[str]:
        """Convenience method to get opportunity ID."""
        ctx = _current_context.get()
        return ctx.scope.opportunity_id if ctx else None

    @staticmethod
    def get_account_id() -> Optional[str]:
        """Convenience method to get account ID."""
        ctx = _current_context.get()
        return ctx.scope.account_id if ctx else None

    @staticmethod
    def clear() -> None:
        """Clear the current context (call at end of request)."""
        _current_context.set(None)
