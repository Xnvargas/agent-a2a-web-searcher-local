"""
=============================================================================
GRAPH DATABASE - LangChain AGEGraph wrapper
=============================================================================

Shared Apache AGE graph access using langchain-community's AGEGraph.
Handles LOAD 'age', search_path setup, Cypher-to-SQL translation,
and agtype result parsing automatically.

=============================================================================
"""

import os
from urllib.parse import urlparse
from langchain_community.graphs.age_graph import AGEGraph

_graph_instance = None


def _parse_db_url(url: str) -> dict:
    """
    Parse DATABASE_URL into psycopg2 connection config.

    Converts: postgresql+psycopg2://user:pass@host:port/dbname
    Into: {"host": "...", "port": ..., "dbname": "...", "user": "...", "password": "..."}
    """
    parsed = urlparse(url.replace("postgresql+psycopg2://", "postgresql://"))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/") or "opp_tracker",
        "user": parsed.username or "postgres",
        "password": parsed.password or "postgres",
    }


def get_age_graph() -> AGEGraph:
    """
    Get the shared AGEGraph instance for the opp_tracker graph.

    AGEGraph handles:
    - LOAD 'age' and search_path setup
    - Cypher to PostgreSQL SQL translation
    - agtype result parsing
    - Schema introspection (node labels, edge labels, properties)

    create=False because the graph already exists (created during DB init).
    """
    global _graph_instance
    if _graph_instance is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/opp_tracker"
        )
        conf = _parse_db_url(db_url)
        _graph_instance = AGEGraph(
            graph_name="opp_tracker",
            conf=conf,
            create=False,
        )
    return _graph_instance


def run_cypher(query: str) -> list[dict]:
    """
    Execute a Cypher query against the opp_tracker graph.

    AGEGraph.query() handles:
    - Cypher to ag_catalog.cypher() SQL wrapping
    - RETURN field projection
    - agtype result parsing to Python dicts

    Returns list of dicts with named fields from RETURN clause.
    """
    graph = get_age_graph()
    return graph.query(query)
