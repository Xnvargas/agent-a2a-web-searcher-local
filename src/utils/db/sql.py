"""
=============================================================================
SQL DATABASE - LangChain SQLDatabase wrapper
=============================================================================

Shared SQL database access using langchain-community's SQLDatabase.
Uses psycopg2 driver (compatible with AGEGraph's psycopg2 dependency).

=============================================================================
"""

import os
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import text

_db_instance = None


def get_sql_database() -> SQLDatabase:
    """
    Get the shared SQLDatabase instance.

    Uses psycopg2 driver (synchronous) which is compatible with
    AGEGraph's psycopg2 dependency — keeps us on one driver.

    Only exposes the tables the agent needs (security + performance).
    """
    global _db_instance
    if _db_instance is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/opp_tracker"
        )
        _db_instance = SQLDatabase.from_uri(
            db_url,
            include_tables=[
                "accounts",
                "opportunities",
                "products",
                "contacts",
                "solutions",
                "documents",
                "document_chunks",
                "opportunity_products",
                "opportunity_contacts",
                "account_products",
                "account_team_members",
                "team_members",
                "team_member_products",
                "document_accounts",
                "document_opportunities",
                "document_solutions",
                "document_contacts",
                "document_products",
            ],
            sample_rows_in_table_info=2,
        )
    return _db_instance


def run_query(sql: str) -> str:
    """Execute a SQL query via LangChain SQLDatabase and return results as string."""
    db = get_sql_database()
    return db.run(sql)


def run_query_params(sql: str, params: dict) -> str:
    """
    Execute a parameterized SQL query using the shared SQLDatabase engine.

    Uses SQLAlchemy text() with explicit bind parameters, bypassing
    LangChain's db.run() which can misinterpret :name patterns in
    raw content (markdown, URLs, JSON, etc.).

    Args:
        sql: SQL string with :named placeholders (e.g., :content, :doc_id)
        params: Dict mapping placeholder names to values

    Returns:
        String representation of results (for SELECT) or row count info.

    Example:
        run_query_params(
            "UPDATE documents SET extracted_text = :content WHERE id = :doc_id::uuid",
            {"content": markdown_text, "doc_id": "abc-123"}
        )
    """
    db = get_sql_database()
    with db._engine.connect() as conn:
        result = conn.execute(text(sql), params)
        conn.commit()
        if result.returns_rows:
            rows = result.fetchall()
            return str(rows)
        return f"{result.rowcount} row(s) affected"


def get_table_info(tables: list[str] = None) -> str:
    """Get schema information for specified tables."""
    db = get_sql_database()
    if tables:
        return db.get_table_info(table_names=tables)
    return db.get_table_info()
