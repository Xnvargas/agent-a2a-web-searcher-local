"""
=============================================================================
CREATE DOCUMENT ARTIFACT TOOL
=============================================================================

Create agent-generated documents and link to current entity.
Uses direct SQLDatabase INSERT + MinIO SDK.

FIXES (from debug session):
  1. Category enum validation — agent was passing invalid values like
     "Documentation" and "Technical". Now validates against the actual
     PostgreSQL document_category enum and falls back to 'agent-artifact'.
  2. Parameterized queries — extracted_text content containing colons
     (markdown, JSON, URLs) was being misinterpreted by SQLAlchemy's
     text() as named bind parameters. Now uses run_query_params().
  3. Condensed error messages — full SQL + content was being echoed
     back to the agent, filling the context window. Errors are now
     concise for the agent, with full detail only in server logs.

=============================================================================
"""

import uuid
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.sql import run_query, run_query_params
from utils.storage.minio_client import upload_to_minio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid PostgreSQL document_category enum values
# Base enum + expansion values from migration
# ---------------------------------------------------------------------------
VALID_CATEGORIES = frozenset({
    # Base enum
    'product-docs',
    'architecture-pattern',
    'case-study',
    'whitepaper',
    'presentation',
    'internal-guide',
    # Expansion (document-system-implementation-plan Phase 2.3)
    'proposal',
    'contract',
    'meeting-notes',
    'email-thread',
    'rfp-response',
    'technical-spec',
    'competitive-analysis',
    'agent-artifact',
})

DEFAULT_CATEGORY = 'agent-artifact'

VALID_SEARCH_MODES = frozenset({'none', 'fulltext', 'semantic'})


def _validate_category(raw: str) -> str:
    """
    Validate and normalise a category value against the PostgreSQL enum.

    Returns a valid enum value, falling back to DEFAULT_CATEGORY with a
    log warning if the input doesn't match.
    """
    normalised = raw.strip().lower() if raw else DEFAULT_CATEGORY
    if normalised in VALID_CATEGORIES:
        return normalised
    logger.warning(
        "Invalid document_category '%s' — falling back to '%s'. "
        "Valid values: %s",
        raw, DEFAULT_CATEGORY, ', '.join(sorted(VALID_CATEGORIES))
    )
    return DEFAULT_CATEGORY


class CreateDocumentArtifactTool(LangChainTool):
    """
    Create a document artifact (generated content) and link to current entity.

    Uses SQLDatabase for record creation and MinIO SDK for file storage.
    """

    name = "create_document_artifact"
    description = (
        "Create a document artifact (analysis, summary, proposal) and optionally "
        "link to the current entity. Documents are saved and become searchable. "
        "Use this to save generated content for future reference. Supports markdown."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        category_list = ', '.join(sorted(VALID_CATEGORIES))
        return {
            "title": {
                "type": "string",
                "required": True,
                "description": "Document title (descriptive, used for search)"
            },
            "content": {
                "type": "string",
                "required": True,
                "description": "Document content (markdown supported)"
            },
            "category": {
                "type": "string",
                "required": False,
                "default": DEFAULT_CATEGORY,
                "enum": sorted(VALID_CATEGORIES),
                "description": (
                    f"Document category. Must be one of: {category_list}. "
                    f"Defaults to '{DEFAULT_CATEGORY}' if omitted or invalid."
                )
            },
            "link_to_current": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": (
                    "Whether to link to current opportunity/account (default: true)"
                )
            },
            "search_mode": {
                "type": "string",
                "required": False,
                "default": "fulltext",
                "enum": sorted(VALID_SEARCH_MODES),
                "description": (
                    "How this document should be searchable: "
                    "'fulltext' (default — fast ranked text search), "
                    "'semantic' (chunked + embedded for similarity search, "
                    "best for long/complex docs), "
                    "'none' (stored but not searchable). "
                    "Suggest 'semantic' for documents >5 pages or technical content. "
                    "Suggest 'fulltext' for short summaries, notes, and artifacts."
                )
            }
        }

    async def execute(
            self,
            title: str,
            content: str,
            category: str = DEFAULT_CATEGORY,
            link_to_current: bool = True,
            search_mode: str = "fulltext"
        ) -> str:
        """Create a document artifact via SQLDatabase + MinIO."""
        try:
            # ----------------------------------------------------------
            # Input validation
            # ----------------------------------------------------------
            if not title or len(title.strip()) < 3:
                return (
                    "Error: Please provide a meaningful title "
                    "(at least 3 characters)."
                )
            if not content or len(content.strip()) < 10:
                return (
                    "Error: Please provide meaningful content "
                    "(at least 10 characters)."
                )

            validated_category = _validate_category(category)
            search_mode_value = (
                search_mode if search_mode in VALID_SEARCH_MODES
                else 'fulltext'
            )

            doc_id = str(uuid.uuid4())
            filename = f"{title.strip()}.md"
            minio_path = f"artifacts/{doc_id}/{filename}"

            # ----------------------------------------------------------
            # 1. Store content in MinIO
            # ----------------------------------------------------------
            await upload_to_minio(
                minio_path, content.encode('utf-8'), "text/markdown"
            )

            # ----------------------------------------------------------
            # 2. Create document record (parameterized)
            # ----------------------------------------------------------
            run_query_params(
                """
                INSERT INTO documents
                    (id, title, filename, file_path, mime_type,
                     file_size_bytes, category, status, source)
                VALUES
                    (:doc_id ::uuid, :title, :filename, :file_path,
                     'text/markdown', :file_size,
                     :category ::document_category,
                     'uploaded', 'agent')
                """,
                {
                    "doc_id": doc_id,
                    "title": title.strip(),
                    "filename": filename,
                    "file_path": minio_path,
                    "file_size": len(content),
                    "category": validated_category,
                }
            )

            # ----------------------------------------------------------
            # 3. Link to current entity (context-aware)
            # ----------------------------------------------------------
            linked_entities = []
            if link_to_current:
                ctx = SWOTContext.get_current()
                if ctx:
                    scope = ctx.scope
                    if scope.opportunity_id:
                        run_query_params(
                            """
                            INSERT INTO document_opportunities
                                (document_id, opportunity_id, context)
                            VALUES (
                                :doc_id ::uuid,
                                :opp_id ::uuid,
                                'agent-generated'
                            )
                            ON CONFLICT DO NOTHING
                            """,
                            {
                                "doc_id": doc_id,
                                "opp_id": scope.opportunity_id,
                            }
                        )
                        linked_entities.append(
                            f"opportunity "
                            f"({ctx.summary.entity_name or scope.opportunity_id})"
                        )
                    if scope.account_id:
                        run_query_params(
                            """
                            INSERT INTO document_accounts
                                (document_id, account_id, context)
                            VALUES (
                                :doc_id ::uuid,
                                :acc_id ::uuid,
                                'agent-generated'
                            )
                            ON CONFLICT DO NOTHING
                            """,
                            {
                                "doc_id": doc_id,
                                "acc_id": scope.account_id,
                            }
                        )
                        linked_entities.append(
                            f"account "
                            f"({ctx.summary.account_name or scope.account_id})"
                        )

            # ----------------------------------------------------------
            # 4. Set search mode and make searchable
            # ----------------------------------------------------------
            if search_mode_value == 'fulltext':
                run_query_params(
                    """
                    UPDATE documents
                    SET search_mode = 'fulltext',
                        extracted_text = :content,
                        status = 'ready',
                        updated_at = NOW()
                    WHERE id = :doc_id ::uuid
                    """,
                    {"content": content, "doc_id": doc_id}
                )
            elif search_mode_value == 'semantic':
                run_query_params(
                    """
                    UPDATE documents
                    SET search_mode = 'semantic'
                    WHERE id = :doc_id ::uuid
                    """,
                    {"doc_id": doc_id}
                )
            else:
                run_query_params(
                    """
                    UPDATE documents
                    SET search_mode = 'none'
                    WHERE id = :doc_id ::uuid
                    """,
                    {"doc_id": doc_id}
                )

            # ----------------------------------------------------------
            # 5. Build confirmation message
            # ----------------------------------------------------------
            result_lines = [
                "Document artifact created successfully!\n",
                f"- **Title:** {title.strip()}",
                f"- **Document ID:** {doc_id}",
                f"- **Category:** {validated_category}",
                f"- **Search mode:** {search_mode_value}",
            ]

            if search_mode_value == 'fulltext':
                result_lines.append(
                    "- **Status:** Ready (instantly searchable)"
                )
            elif search_mode_value == 'semantic':
                result_lines.append(
                    "- **Status:** Awaiting semantic processing "
                    "(chunking + embedding)"
                )
            else:
                result_lines.append(
                    "- **Status:** Stored (not searchable)"
                )

            if linked_entities:
                result_lines.append(
                    f"- **Linked to:** {', '.join(linked_entities)}"
                )
            else:
                result_lines.append("- **Linked to:** None (global)")

            return '\n'.join(result_lines)

        except Exception as e:
            # Full detail → server logs only
            logger.exception(
                "create_document_artifact failed for title='%s', "
                "category='%s'",
                title[:80] if title else '(empty)',
                category,
            )
            # Condensed message → agent context
            error_type = type(e).__name__
            error_brief = str(e)[:200]
            return (
                f"Error creating document ({error_type}): {error_brief}\n\n"
                "Check server logs for full details. "
                "Common fixes: verify category is valid, "
                "ensure MinIO is running."
            )

    def get_langchain_tool(self):
        @tool
        def create_document_artifact(
            title: str,
            content: str,
            category: str = DEFAULT_CATEGORY,
            link_to_current: bool = True,
            search_mode: str = "fulltext"
        ) -> str:
            """Create a document artifact and optionally link to the current entity."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return create_document_artifact
