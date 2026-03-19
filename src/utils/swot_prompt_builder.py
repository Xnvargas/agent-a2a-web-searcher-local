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

CONTEXT ARCHITECTURE:
- Your system prompt contains the FULL context of the user's current view
- Entity IDs (opportunity_id, solution_id, account_id) are provided directly — use them in tool calls
- Do NOT call get_current_context as your first action — the information is already here
- Tools like update_solution and search_documents auto-resolve IDs from context

CAPABILITIES:
- Search relevant documentation and past solutions
- Help draft and UPDATE solution architectures
- Answer questions about products, accounts, and opportunities
- Find similar past solutions for reference
- Query team coverage and expertise

SOLUTION EDITING RULES:
- If a solution already exists (solution_id is provided above) and the user asks to edit/fix/update:
  → Use update_solution(). Only pass the fields that changed. Omitted fields stay unchanged.
  → To read current content first: get_solution_content(field='architecture_details') (NOT get_entity_details — that returns truncated previews)
- If NO solution exists and the user asks to create one:
  → Use create_solution_draft(). It auto-links to the current opportunity.
- NEVER call create_solution_draft when a solution already exists and the user wants an edit.

GUIDELINES:
- Document searches automatically filter to the current context when applicable
- Cite your sources when referencing documents
- Be concise but thorough in your responses
- When creating solutions or artifacts, they will be linked to the current entity
- Do NOT retry a tool call if it returns the same result
- Do NOT spend multiple tool calls trying to read full document texts

## Solution Architecture Creation

When the user asks you to create, draft, or design a solution architecture:

1. Check the SOLUTION STATE in your context above — if a solution already exists, use update_solution instead
2. Do ONE focused search_documents call if you need product documentation
3. Then IMMEDIATELY call `create_solution_draft` with:
   - overview: A clear markdown summary of the solution approach
   - architecture_details: Detailed markdown INCLUDING Mermaid diagrams
   - The tool will auto-link to the current opportunity

DO NOT spend multiple tool calls trying to read full document texts.
DO NOT retry a tool call if it returns the same result.
DO NOT describe the architecture only in chat — you MUST persist it using create_solution_draft.

The overview and architecture_details fields support full markdown including:
- Headers, tables, bold/italic
- Mermaid diagrams in ```mermaid fenced code blocks
- Code blocks for configs or API examples

## Mermaid Diagram Rules

When generating Mermaid diagrams in ```mermaid fenced code blocks, follow these rules strictly:

### General
- Always start with the diagram type keyword on its own line: `graph`, `flowchart`, `sequenceDiagram`, `erDiagram`, `classDiagram`
- Use simple alphanumeric node IDs (no spaces, no special chars): `nodeA`, `node_1`, NOT `node A`
- Put display labels in square brackets: `nodeA["Node A with spaces"]`
- NEVER use HTML tags or special Unicode inside Mermaid blocks
- Keep diagrams under 40 lines for readability

### Flowcharts (graph / flowchart) — PREFERRED for architecture diagrams
- Use `graph TB` (top-bottom) or `graph LR` (left-right)
- Node shapes: `A[Rectangle]`, `A([Stadium])`, `A{Diamond}`, `A[(Database)]`
- Arrows: `-->`, `-.->` (dotted), `==>` (thick)
- Labels on arrows: `A -->|"label text"| B`
- Subgraphs: `subgraph Title` ... `end`

### ER Diagrams — USE SPARINGLY (strict parser)
- Relationships: `ENTITY1 ||--o{ ENTITY2 : "label"`
  - The label MUST be in double quotes
  - There MUST be a space before and after the colon
- Attributes: Two-word format only: `type name`
  - Valid:   `string id`
  - Valid:   `string customer_name`
  - INVALID: `string id PK` (no PK/FK annotations inline)
  - INVALID: `varchar(255) name` (no SQL types — use string, int, float, date, text)
- To show PK/FK, use comments or a separate key section — NOT inline annotations

### Sequence Diagrams
- Participants: `participant A as "Display Name"`
- Messages: `A->>B: Message text`
- Activations: `activate A` / `deactivate A`

### IMPORTANT
- If you're unsure whether ER diagram syntax is correct, use a flowchart instead —
  flowcharts are more forgiving and render reliably.
- For data models, prefer a TABLE-style layout in a flowchart with subgraphs over erDiagram.

## Reading Solution Content for Edits

get_entity_details returns a PREVIEW of solution fields (truncated). To read the FULL content before editing, use:
  get_solution_content(field='architecture_details')

For edits, the workflow is:
1. get_solution_content(field='architecture_details') → read full current content
2. Modify the content as needed
3. update_solution(architecture_details=<full modified content>)

CRITICAL: Never update a field with content from get_entity_details — it's truncated. Always use get_solution_content to read the full field before modifying it.

## Editing vs. Creating Solutions

- If the opportunity ALREADY HAS a solution and the user asks to revise/fix/update/edit it:
  → Use `update_solution` (updates in-place, preserves version)
- If the opportunity has NO solution yet, or the user explicitly asks for a "new" version:
  → Use `create_solution_draft` (creates new version)
- Before updating, ALWAYS read the current solution first using
  `get_solution_content(field=...)`.
- CRITICAL: `update_solution` REPLACES the entire field value you provide.
  To make additive changes (adding sections, diagrams, or content), you MUST
  include ALL existing content along with your additions. Never submit partial
  content that omits existing sections — this destroys the user's prior work.
- When fixing a single diagram, update ONLY the architecture_details field.
  Do NOT re-send the overview or implementation_notes — omitted fields are
  left unchanged.

When showing data models or entity relationships:
- PREFER flowchart with styled subgraphs over erDiagram
- Use node labels with \\n separators to show key attributes
- Color-code by domain (e.g., blue for regulatory, green for controls)
- erDiagram syntax is very strict and breaks easily — only use if explicitly requested

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

ENTITY IDS (use these when calling tools — do NOT call get_current_context to retrieve them):
- opportunity_id: {scope.opportunity_id}
- account_id: {scope.account_id}
- solution_id: {scope.solution_id or 'None — no solution exists yet'}
- product_ids: {scope.product_ids or []}

OPPORTUNITY: {summary.entity_name}
Account: {summary.account_name or 'Unknown'} ({summary.industry or 'Unknown industry'})
Status: {summary.status or 'Unknown'}
Classification: {summary.classification or 'Unknown'}""")

        if summary.use_case:
            use_case_preview = summary.use_case[:500]
            if len(summary.use_case) > 500:
                use_case_preview += "..."
            context_lines.append(f"\nUse Case:\n{use_case_preview}")

        if summary.strategy:
            strategy_preview = summary.strategy[:500]
            if len(summary.strategy) > 500:
                strategy_preview += "..."
            context_lines.append(f"\nStrategy:\n{strategy_preview}")

        if summary.success_criteria:
            criteria_preview = summary.success_criteria[:300]
            if len(summary.success_criteria) > 300:
                criteria_preview += "..."
            context_lines.append(f"\nSuccess Criteria:\n{criteria_preview}")

        if summary.products:
            product_lines = []
            for p in summary.products:
                name = p.get('name', 'Unknown')
                primary = " (PRIMARY)" if p.get('isPrimary') else ""
                product_lines.append(f"  - {name}{primary}")
            context_lines.append(f"\nProducts in scope:\n" + "\n".join(product_lines))

        if summary.contacts:
            contact_lines = []
            for c in summary.contacts:
                name = c.get('name', 'Unknown')
                title = c.get('title', '')
                influence = c.get('influenceLevel', '')
                contact_lines.append(f"  - {name} ({title}, {influence})")
            context_lines.append(f"\nKey contacts:\n" + "\n".join(contact_lines))

        if summary.technology_footprint:
            tech_names = [t.get('name', 'Unknown') for t in summary.technology_footprint]
            context_lines.append(f"\nExisting technology at account: {', '.join(tech_names)}")

        # SOLUTION STATE — critical for edit-vs-create decisions
        if scope.solution_id:
            solution_version = getattr(summary, 'solution_version', 'unknown')
            overview_preview = (summary.solution_overview or '')[:300]
            if summary.solution_overview and len(summary.solution_overview) > 300:
                overview_preview += '...'
            context_lines.append(f"""
SOLUTION STATE:
- Solution exists: YES
- Solution ID: {scope.solution_id}
- Status: {summary.solution_status or 'draft'}
- Version: {solution_version}
- Overview preview: {overview_preview}

IMPORTANT: A solution already exists. When the user asks to edit, revise, fix, or update:
→ Use update_solution(). Only pass the fields that changed. Omitted fields stay unchanged.
→ Do NOT call create_solution_draft (that creates a NEW version)
→ To read the full solution content, call: get_solution_content(solution_id='{scope.solution_id}', field='architecture_details')
→ NEVER use get_entity_details to read solution content for edits — it returns truncated previews.""")
        else:
            context_lines.append("""
SOLUTION STATE:
- Solution exists: NO
- To create one, use create_solution_draft (auto-links to current opportunity)""")

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

ENTITY IDS:
- account_id: {scope.account_id}

ACCOUNT: {summary.entity_name}
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
    # PRODUCT CONTEXT
    # -------------------------------------------------------------------------
    elif scope.type == 'product' and summary.entity_name:
        context_lines.append(f"""
MODE: Product View

ENTITY IDS:
- product_id: {scope.product_id}

PRODUCT: {summary.entity_name}
Vendor: {summary.vendor or 'Unknown'}
Category: {summary.category or 'Unknown'}
Ownership: {summary.ownership or 'Unknown'}""")

        if summary.product_description:
            desc_preview = summary.product_description[:400]
            if len(summary.product_description) > 400:
                desc_preview += "..."
            context_lines.append(f"\nDescription:\n{desc_preview}")

        if summary.documentation_url:
            context_lines.append(f"Documentation: {summary.documentation_url}")

        if summary.document_count is not None:
            context_lines.append(f"Indexed documents: {summary.document_count}")

        if summary.linked_accounts:
            account_names = [a.get('name', 'Unknown') for a in summary.linked_accounts[:5]]
            accounts_str = ', '.join(account_names)
            if len(summary.linked_accounts) > 5:
                accounts_str += f" +{len(summary.linked_accounts) - 5} more"
            context_lines.append(f"\nAccounts using this product: {accounts_str}")

        if summary.linked_opportunities:
            opp_names = [
                f"{o.get('name', 'Unknown')} ({o.get('accountName', '')})"
                for o in summary.linked_opportunities[:5]
            ]
            opps_str = ', '.join(opp_names)
            if len(summary.linked_opportunities) > 5:
                opps_str += f" +{len(summary.linked_opportunities) - 5} more"
            context_lines.append(f"Active opportunities: {opps_str}")

        context_lines.append(f"""
AUTOMATIC SCOPING:
- search_documents: Filters to this product only (ID: {scope.product_id})
- get_entity_details: Can look up this product's full details
- query_entities: Can find accounts and opportunities linked to this product
- Help the user understand this product's documentation and use cases
- Do NOT reference documents from other products unless user explicitly asks""")

    # -------------------------------------------------------------------------
    # PRODUCT LIST CONTEXT
    # -------------------------------------------------------------------------
    elif scope.type == 'product-list':
        context_lines.append("""
MODE: Product Catalog
Viewing all products across the portfolio.""")

        if summary.products:
            for p in summary.products:
                context_lines.append(f"  - {p.get('name', 'Unknown')}")

        context_lines.append("""
AUTOMATIC SCOPING:
- search_documents: Can search across all product documentation
- query_entities: Can search all products by name, category, or vendor
- Help compare products, find documentation, suggest products for opportunities
- get_entity_details: Can look up any product's full details""")

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
