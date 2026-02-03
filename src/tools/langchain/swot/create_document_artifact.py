"""
=============================================================================
CREATE DOCUMENT ARTIFACT TOOL
=============================================================================

Create agent-generated documents and link to current entity.
Documents are stored in MinIO and processed for embedding.

=============================================================================
"""

import os
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.swot_context import SWOTContext


class CreateDocumentArtifactTool(LangChainTool):
    """
    Create a document artifact (generated content) and link to current entity.

    Use this to save analyses, summaries, proposals, or any generated content
    that should be searchable and linked to the business context.
    """

    name = "create_document_artifact"
    description = (
        "Create a document artifact (analysis, summary, proposal) and optionally "
        "link to the current entity. Documents are saved and become searchable. "
        "Use this to save generated content for future reference. Supports markdown."
    )

    api_base_url: str = os.getenv("SWOT_API_BASE", "http://localhost:3000")
    timeout: float = 30.0

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
            }
        }

    async def execute(
        self,
        title: str,
        content: str,
        category: str = "agent-artifact",
        link_to_current: bool = True
    ) -> str:
        """Create a document artifact."""
        try:
            # Validate inputs
            if not title or len(title.strip()) < 3:
                return "Please provide a meaningful title (at least 3 characters)."
            if not content or len(content.strip()) < 10:
                return "Please provide meaningful content (at least 10 characters)."

            # Build request
            payload: Dict[str, Any] = {
                "title": title.strip(),
                "content": content.strip(),
                "category": category,
                "mimeType": "text/markdown"
            }

            # Link to current context if requested
            linked_entities = []
            if link_to_current:
                ctx = SWOTContext.get_current()
                if ctx:
                    scope = ctx.scope
                    if scope.opportunity_id:
                        payload['opportunityId'] = scope.opportunity_id
                        linked_entities.append(f"opportunity ({ctx.summary.entity_name or scope.opportunity_id})")
                    if scope.account_id:
                        payload['accountId'] = scope.account_id
                        linked_entities.append(f"account ({ctx.summary.account_name or scope.account_id})")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/api/documents/artifacts",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

            doc_id = data.get('id', 'unknown')

            # Build confirmation message
            result = [
                f"Document artifact created successfully!\n",
                f"- **Title:** {title}",
                f"- **Document ID:** {doc_id}",
                f"- **Category:** {category}",
            ]

            if linked_entities:
                result.append(f"- **Linked to:** {', '.join(linked_entities)}")
            else:
                result.append("- **Linked to:** None (global)")

            result.append(f"\nThe document will be processed and become searchable shortly.")

            return '\n'.join(result)

        except httpx.HTTPStatusError as e:
            return f"API error: {e.response.status_code} - {e.response.text}"
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
