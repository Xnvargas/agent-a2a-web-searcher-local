"""
=============================================================================
DATABASE UTILITIES - LangChain-native database access layer
=============================================================================

Shared infrastructure for direct database access using LangChain integrations:

- embeddings.py: AgentEmbedder (ollama SDK with Matryoshka dimensions)
- sql.py: SQLDatabase (langchain-community) + parameterized query helper
- graph.py: AGEGraph (langchain-community)
- vector_search.py: Composition layer (embeddings + sql for pgvector queries)

=============================================================================
"""

from .embeddings import (
    get_embedder,
    get_embeddings,  # backwards-compatible alias for get_embedder
    generate_embedding,
    generate_embeddings_batch,
)
from .sql import get_sql_database, run_query, run_query_params, get_table_info
from .graph import get_age_graph, run_cypher
from .vector_search import search_documents, search_documents_fulltext, find_similar_solutions

__all__ = [
    'get_embedder', 'get_embeddings',
    'generate_embedding', 'generate_embeddings_batch',
    'get_sql_database', 'run_query', 'run_query_params', 'get_table_info',
    'get_age_graph', 'run_cypher',
    'search_documents', 'search_documents_fulltext', 'find_similar_solutions',
]
