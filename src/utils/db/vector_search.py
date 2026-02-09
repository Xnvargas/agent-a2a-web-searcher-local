"""
=============================================================================
VECTOR SEARCH - Composition layer (AgentEmbedder + SQLDatabase)
=============================================================================

Combines AgentEmbedder (ollama SDK) for query vector generation with
SQLDatabase.run() to call our existing PostgreSQL search functions.

Uses the existing search_documents() and find_similar_solutions() SQL
functions that encapsulate the complex entity-scoped filtering logic.

=============================================================================
"""

from utils.db.embeddings import generate_embedding
from utils.db.sql import run_query


async def search_documents(
    query_text: str,
    account_id: str = None,
    opportunity_id: str = None,
    solution_id: str = None,
    contact_id: str = None,
    product_ids: list[str] = None,
    limit: int = 10,
    threshold: float = 0.7,
) -> str:
    """
    Semantic document search using pgvector.

    1. Generates embedding via AgentEmbedder (ollama SDK)
    2. Calls search_documents() PostgreSQL function via LangChain SQLDatabase

    This reuses the same SQL function the Next.js API calls,
    just without the HTTP proxy hop.
    """
    embedding = await generate_embedding(query_text)
    embedding_str = f"'[{','.join(str(x) for x in embedding)}]'::vector"

    # Build parameter expressions for SQL
    acc = f"'{account_id}'::uuid" if account_id else "NULL"
    opp = f"'{opportunity_id}'::uuid" if opportunity_id else "NULL"
    sol = f"'{solution_id}'::uuid" if solution_id else "NULL"
    con = f"'{contact_id}'::uuid" if contact_id else "NULL"

    if product_ids:
        pids = ",".join(f"'{p}'::uuid" for p in product_ids)
        prod = f"ARRAY[{pids}]"
    else:
        prod = "NULL"

    sql = f"""
        SELECT * FROM search_documents(
            {embedding_str}, {acc}, {opp}, {sol}, {con}, {prod}, {limit}, {threshold}
        )
    """

    return run_query(sql)


async def find_similar_solutions(
    use_case_text: str,
    limit: int = 5,
    min_similarity: float = 0.7,
    exclude_opportunity_id: str = None,
) -> str:
    """
    Find solutions similar to a use case description.

    1. Generates embedding via AgentEmbedder (ollama SDK)
    2. Calls find_similar_solutions() PostgreSQL function via LangChain SQLDatabase
    """
    embedding = await generate_embedding(use_case_text)
    embedding_str = f"'[{','.join(str(x) for x in embedding)}]'::vector"

    exclude = f"'{exclude_opportunity_id}'::uuid" if exclude_opportunity_id else "NULL"

    sql = f"""
        SELECT * FROM find_similar_solutions(
            {embedding_str}, {limit}, {min_similarity}, {exclude}
        )
    """

    return run_query(sql)
