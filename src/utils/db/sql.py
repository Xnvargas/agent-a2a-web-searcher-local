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
    """Execute a read-only SQL query and return results as string."""
    db = get_sql_database()
    return db.run(sql)


def get_table_info(tables: list[str] = None) -> str:
    """Get schema information for specified tables."""
    db = get_sql_database()
    if tables:
        return db.get_table_info(table_names=tables)
    return db.get_table_info()
