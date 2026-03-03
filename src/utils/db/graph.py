"""
=============================================================================
GRAPH DATABASE - LangChain AGEGraph wrapper
=============================================================================

Shared Apache AGE graph access using langchain-community's AGEGraph.
Handles LOAD 'age', search_path setup, Cypher-to-SQL translation,
and agtype result parsing automatically.

Write operations use raw psycopg2 with explicit commit, since
AGEGraph.query() doesn't reliably persist writes in long-running
server processes.

=============================================================================
"""

import os
import json
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

    Routes to AGEGraph.query() for reads (automatic agtype parsing)
    or raw psycopg2 cursor for writes (explicit commit for persistence).
    """
    graph = get_age_graph()

    write_keywords = ('CREATE', 'SET ', 'DELETE', 'MERGE', 'REMOVE', 'DETACH')
    query_upper = query.strip().upper()
    is_write = any(kw in query_upper for kw in write_keywords)

    if is_write:
        return _execute_write(graph, query)
    else:
        return graph.query(query)


def _execute_write(graph: AGEGraph, cypher_query: str) -> list[dict]:
    """
    Execute a write Cypher query using raw psycopg2 with explicit commit.

    AGEGraph.query() doesn't reliably commit writes in long-running
    server processes. This function uses the underlying connection
    directly with LOAD 'age', search_path setup, and explicit commit.
    """
    conn = graph.connection

    sql = f"""
        SELECT * FROM cypher('{graph.graph_name}', $$
            {cypher_query}
        $$) AS (result agtype)
    """

    cur = conn.cursor()
    try:
        cur.execute("LOAD 'age';")
        cur.execute('SET search_path = ag_catalog, "$user", public;')
        cur.execute(sql)

        rows = []
        try:
            rows = cur.fetchall()
        except Exception:
            pass  # Some writes (DETACH DELETE) may not return rows

        conn.commit()

        # Parse agtype results into dicts
        results = []
        for row in rows:
            if row and row[0]:
                raw = str(row[0])
                # AGE returns agtype with ::vertex or ::edge suffix
                # Strip the type suffix and try to parse as JSON
                for suffix in ('::vertex', '::edge', '::path'):
                    raw = raw.replace(suffix, '')
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict) and 'properties' in parsed:
                        results.append(parsed['properties'])
                    else:
                        results.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    results.append({"result": str(row[0])})

        return results

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()