"""
=============================================================================
SWOT CONTEXT - Context Management for SWOT Agent Tools
=============================================================================

Provides async-safe context storage that tools can access to automatically
scope their queries to the current entity (opportunity, account, etc.).

USAGE IN AGENT HANDLER:
-----------------------
```python
from utils.swot_context import SWOTContext, extract_swot_context_from_message

# Extract context from A2A message metadata (frontend passes it here)
swot_ctx = extract_swot_context_from_message(input)
SWOTContext.set_current(swot_ctx)
```

NOTE: AgentStack doesn't expose params.extensions to agent functions.
The frontend passes SWOT context in message.metadata['swot-context'].

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
    type: str = "global"  # 'global', 'opportunity', 'account', 'solution', 'dashboard', 'product', 'product-list'
    opportunity_id: Optional[str] = None
    account_id: Optional[str] = None
    solution_id: Optional[str] = None
    product_id: Optional[str] = None        # Single product focus (scope.type == 'product')
    product_ids: Optional[List[str]] = None  # Filter list for document search

    def has_opportunity_scope(self) -> bool:
        """Check if we have opportunity-level scope."""
        return self.type in ('opportunity', 'solution') and self.opportunity_id is not None

    def has_account_scope(self) -> bool:
        """Check if we have account-level scope."""
        return self.type in ('opportunity', 'account', 'solution') and self.account_id is not None

    def has_product_scope(self) -> bool:
        """Check if we have single-product scope."""
        return self.type == 'product' and self.product_id is not None

    def has_product_list_scope(self) -> bool:
        """Check if we're in product-list mode (all products)."""
        return self.type == 'product-list'

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
        if self.product_id:
            filters['productId'] = self.product_id
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

    # Product fields (when scope.type == 'product' or 'product-list')
    vendor: Optional[str] = None
    ownership: Optional[str] = None
    category: Optional[str] = None
    product_description: Optional[str] = None
    documentation_url: Optional[str] = None
    document_count: Optional[int] = None
    linked_accounts: Optional[List[Dict[str, Any]]] = None
    linked_opportunities: Optional[List[Dict[str, Any]]] = None


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
        product_id=scope_data.get('productId'),
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
        team_members=summary_data.get('teamMembers'),
        # Product fields
        vendor=summary_data.get('vendor'),
        ownership=summary_data.get('ownership'),
        category=summary_data.get('category'),
        product_description=summary_data.get('productDescription'),
        documentation_url=summary_data.get('documentationUrl'),
        document_count=summary_data.get('documentCount'),
        linked_accounts=summary_data.get('linkedAccounts'),
        linked_opportunities=summary_data.get('linkedOpportunities'),
    )

    return SWOTContextData(
        scope=scope,
        summary=summary,
        fetched_at=ctx_data.get('fetchedAt')
    )


def extract_swot_context_from_message(message) -> Optional[SWOTContextData]:
    """
    Extract SWOTContextData from A2A message metadata.

    The frontend passes SWOT context in message.metadata['swot-context']
    because AgentStack doesn't expose params.extensions to agent functions.

    Args:
        message: The A2A Message object (from a2a.types)

    Returns:
        SWOTContextData if context present in metadata, None otherwise

    Example message structure:
        Message(
            role='user',
            parts=[TextPart(text='...')],
            metadata={'swot-context': {...}}
        )
    """
    if not message:
        print("[SWOT Context] No message provided")
        return None

    # Access metadata attribute - may be None or dict
    metadata = getattr(message, 'metadata', None)
    if not metadata:
        print("[SWOT Context] No metadata in message")
        return None

    # Look for swot-context key in metadata
    swot_ctx_data = metadata.get('swot-context')
    if not swot_ctx_data:
        print("[SWOT Context] No 'swot-context' key in metadata")
        print(f"[SWOT Context] Available metadata keys: {list(metadata.keys())}")
        return None

    print(f"[SWOT Context] Found context in message metadata:")
    print(f"  - Scope type: {swot_ctx_data.get('scope', {}).get('type', 'unknown')}")
    print(f"  - Entity: {swot_ctx_data.get('summary', {}).get('entityName', 'None')}")

    # Reuse existing extraction logic by wrapping in expected format
    return extract_swot_context({'context': swot_ctx_data})


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
    def get_product_id() -> Optional[str]:
        """Convenience method to get product ID."""
        ctx = _current_context.get()
        return ctx.scope.product_id if ctx else None

    @staticmethod
    def is_product_scope() -> bool:
        """Check if current scope is product-focused."""
        ctx = _current_context.get()
        return ctx is not None and ctx.scope.type == 'product'

    @staticmethod
    def is_product_list_scope() -> bool:
        """Check if current scope is product-list."""
        ctx = _current_context.get()
        return ctx is not None and ctx.scope.type == 'product-list'

    @staticmethod
    def clear() -> None:
        """Clear the current context (call at end of request)."""
        _current_context.set(None)
