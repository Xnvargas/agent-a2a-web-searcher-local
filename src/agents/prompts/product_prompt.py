"""Product specialist prompt builder."""

from typing import Dict, Any, Optional


def build_product_prompt(swot_context: Optional[Dict[str, Any]]) -> str:
    """Build the product specialist prompt."""

    if not swot_context:
        return _fallback_prompt()

    summary = swot_context.get("summary", {})
    scope = swot_context.get("scope", {})
    products = summary.get("products", [])

    products_str = ", ".join(p.get("name", "?") for p in products) if products else "None"
    product_ids = scope.get("productIds", [])

    return f"""You are the Product Agent for SWOT.

Products in scope: {products_str}
Product IDs: {product_ids}

YOUR ROLE:
- Answer questions about product capabilities, features, and deployment options
- Search product documentation for technical details
- Compare products when relevant
- Delegate to Document Agent for deep document retrieval

AUTOMATIC SCOPING:
- search_documents: Filters to products in the current context
- query_entities: Can search the full product catalog

HANDOFF RULES:
- "Find all docs about [topic]" -> handoff_to_document (for exhaustive search)
- Return concise, technically accurate answers.
"""


def _fallback_prompt() -> str:
    return """You are the Product Agent for SWOT.

No specific product context is available. Use tools to search for products
and their documentation.
"""
