"""
=============================================================================
GET DOCUMENT TEXT TOOL
=============================================================================

Retrieve the full extracted text of a document by ID. Supports pagination
for large documents to avoid context overflow.

=============================================================================
"""

from typing import Dict, Any
from langchain_core.tools import tool

from tools.langchain.base import LangChainTool
from utils.db.sql import run_query


# Maximum chars to return in a single call. Agent can paginate with offset.
MAX_CHARS_PER_CALL = 12000


class GetDocumentTextTool(LangChainTool):
    """
    Retrieve the full extracted text of a document.

    Use after search_documents to read a document's full content.
    Supports offset/length pagination for large documents.
    """

    name = "get_document_text"
    description = (
        "Get the full text content of a document by its ID. Use this after "
        "searching to read a document in detail — for summarizing, analyzing, "
        "or answering questions about its content. For large documents, use "
        "offset to paginate through the text."
    )

    def get_schema(self) -> Dict[str, Dict[str, Any]]:
        return {
            "document_id": {
                "type": "string",
                "required": True,
                "description": "UUID of the document to retrieve text from"
            },
            "offset": {
                "type": "integer",
                "required": False,
                "default": 0,
                "description": (
                    "Character offset to start reading from (default: 0). "
                    "Use this to paginate through large documents."
                )
            },
            "max_length": {
                "type": "integer",
                "required": False,
                "default": MAX_CHARS_PER_CALL,
                "description": (
                    f"Maximum characters to return (default/max: {MAX_CHARS_PER_CALL}). "
                    f"Use smaller values if you only need a section."
                )
            }
        }

    async def execute(
        self,
        document_id: str,
        offset: int = 0,
        max_length: int = MAX_CHARS_PER_CALL,
    ) -> str:
        """Retrieve document text with pagination support."""
        try:
            # Clamp max_length
            max_length = max(100, min(max_length, MAX_CHARS_PER_CALL))
            offset = max(0, offset)

            # Sanitize document_id
            safe_id = document_id.replace("'", "''")

            # Get metadata
            meta_result = run_query(f"""
                SELECT title, status, page_count,
                       COALESCE(LENGTH(extracted_text), 0) AS text_length
                FROM ag_catalog.documents
                WHERE id = '{safe_id}'::uuid
            """)

            if not meta_result or meta_result.strip() == '':
                return f"Document '{document_id}' not found."

            # Get text slice
            text_result = run_query(f"""
                SELECT SUBSTRING(extracted_text FROM {offset + 1} FOR {max_length})
                    AS text_content
                FROM ag_catalog.documents
                WHERE id = '{safe_id}'::uuid
                  AND extracted_text IS NOT NULL
            """)

            if not text_result or text_result.strip() == '':
                return (
                    f"Document '{document_id}' has no extracted text. "
                    f"It may need (re)processing."
                )

            # Build readable response for the agent
            header = f"Document text"
            if offset > 0:
                header += f" (offset: {offset})"
            header += f"\n{'='*60}\n"

            footer = (
                f"\n{'='*60}\n"
                f"Showing up to {max_length} chars from offset {offset}. "
                f"Call again with offset={offset + max_length} to continue reading."
            )

            return f"{header}{text_result}{footer}"

        except Exception as e:
            return f"Error retrieving document text: {str(e)}"

    def get_langchain_tool(self):
        @tool
        def get_document_text(
            document_id: str,
            offset: int = 0,
            max_length: int = MAX_CHARS_PER_CALL,
        ) -> str:
            """Get full text of a document by ID. Supports offset pagination for large docs."""
            return "LANGCHAIN_TOOL_PLACEHOLDER"
        return get_document_text

    def get_citation_metadata(self, tool_args: Dict, tool_result: str) -> Dict:
        return {
            "tool": self.name,
            "document_id": tool_args.get("document_id", ""),
            "source_type": "document_text"
        }
