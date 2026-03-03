"""
=============================================================================
CREATE DOCUMENT ARTIFACT TOOL
=============================================================================

Create agent-generated documents and link to current entity.
Migrated from httpx HTTP proxy to direct SQLDatabase INSERT + MinIO SDK.

=============================================================================
"""

import uuid
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext
from utils.db.sql import run_query
from utils.storage.minio_client import upload_to_minio


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
                "default": "agent-artifact",
                "description": "Document category: agent-artifact, analysis, proposal, summary, technical-spec"
            },
            "link_to_current": {
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Whether to link to current opportunity/account (default: true)"
            },
            "search_mode": {
                "type": "string",
                "required": False,
                "default": "fulltext",
                "description": (
                    "How this document should be searchable: "
                    "'fulltext' (default — fast ranked text search), "
                    "'semantic' (chunked + embedded for similarity search, best for long/complex docs), "
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
            category: str = "agent-artifact",
            link_to_current: bool = True,
            search_mode: str = "fulltext"
        ) -> str:
            """Create a document artifact via SQLDatabase + MinIO."""
            try:
                # Validate inputs
                if not title or len(title.strip()) < 3:
                    return "Please provide a meaningful title (at least 3 characters)."
                if not content or len(content.strip()) < 10:
                    return "Please provide meaningful content (at least 10 characters)."

                doc_id = str(uuid.uuid4())
                safe_title = title.strip().replace("'", "''")
                safe_category = category.replace("'", "''")
                filename = f"{title.strip()}.md"
                safe_filename = filename.replace("'", "''")
                minio_path = f"artifacts/{doc_id}/{filename}"

                # 1. Store content in MinIO
                await upload_to_minio(minio_path, content.encode('utf-8'), "text/markdown")

                # 2. Create document record via LangChain SQLDatabase
                safe_minio_path = minio_path.replace("'", "''")
                run_query(f"""
                    INSERT INTO documents (id, title, filename, file_path, mime_type,
                        file_size_bytes, category, status, source)
                    VALUES ('{doc_id}'::uuid, '{safe_title}', '{safe_filename}', '{safe_minio_path}',
                        'text/markdown', {len(content)}, '{safe_category}', 'uploaded', 'agent')
                """)

                # 3. Link to current entity
                linked_entities = []
                if link_to_current:
                    ctx = SWOTContext.get_current()
                    if ctx:
                        scope = ctx.scope
                        if scope.opportunity_id:
                            run_query(f"""
                                INSERT INTO document_opportunities (document_id, opportunity_id)
                                VALUES ('{doc_id}'::uuid, '{scope.opportunity_id}'::uuid)
                                ON CONFLICT DO NOTHING
                            """)
                            linked_entities.append(
                                f"opportunity ({ctx.summary.entity_name or scope.opportunity_id})"
                            )
                        if scope.account_id:
                            run_query(f"""
                                INSERT INTO document_accounts (document_id, account_id)
                                VALUES ('{doc_id}'::uuid, '{scope.account_id}'::uuid)
                                ON CONFLICT DO NOTHING
                            """)
                            linked_entities.append(
                                f"account ({ctx.summary.account_name or scope.account_id})"
                            )

                # 4. Set search mode and make searchable
                search_mode_value = (
                    search_mode
                    if search_mode in ('none', 'fulltext', 'semantic')
                    else 'fulltext'
                )
                safe_content = content.replace("'", "''")

                if search_mode_value == 'fulltext':
                    run_query(f"""
                        UPDATE documents
                        SET search_mode = 'fulltext',
                            extracted_text = '{safe_content}',
                            status = 'ready',
                            updated_at = NOW()
                        WHERE id = '{doc_id}'::uuid
                    """)
                elif search_mode_value == 'semantic':
                    run_query(f"""
                        UPDATE documents
                        SET search_mode = 'semantic'
                        WHERE id = '{doc_id}'::uuid
                    """)
                else:
                    run_query(f"""
                        UPDATE documents
                        SET search_mode = 'none'
                        WHERE id = '{doc_id}'::uuid
                    """)

                # 5. Build confirmation message
                result_lines = [
                    "Document artifact created successfully!\n",
                    f"- **Title:** {title}",
                    f"- **Document ID:** {doc_id}",
                    f"- **Category:** {category}",
                    f"- **Search mode:** {search_mode_value}",
                ]

                if search_mode_value == 'fulltext':
                    result_lines.append("- **Status:** Ready (instantly searchable)")
                elif search_mode_value == 'semantic':
                    result_lines.append(
                        "- **Status:** Awaiting semantic processing (chunking + embedding)"
                    )
                else:
                    result_lines.append("- **Status:** Stored (not searchable)")

                if linked_entities:
                    result_lines.append(
                        f"- **Linked to:** {', '.join(linked_entities)}"
                    )
                else:
                    result_lines.append("- **Linked to:** None (global)")

                return '\n'.join(result_lines)

            except Exception as e:
                return f"Error creating document: {str(e)}"
    
    def get_langchain_tool(self):
        @tool
        def create_document_artifact(
            title: str,
            content: str,
            category: str = "agent-artifact",
            link_to_current: bool = True
        ) -> str:
            """Create a document artifact and optionally link to the current entity."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return create_document_artifact
