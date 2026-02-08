"""
=============================================================================
EMBEDDINGS - LangChain OllamaEmbeddings wrapper
=============================================================================

Shared embedding generation using langchain-ollama's OllamaEmbeddings.
Matches the Next.js pipeline's qwen3-embedding model (1536 dimensions).

=============================================================================
"""

import os
from langchain_ollama import OllamaEmbeddings

# Singleton instance — reused across all tool calls
_embeddings_instance = None

EXPECTED_DIMS = 1536  # Must match pgvector column: vector(1536)


def get_embeddings() -> OllamaEmbeddings:
    """
    Get the shared OllamaEmbeddings instance.

    Uses qwen3-embedding model matching the Next.js pipeline:
    - Model: qwen3-embedding (same as src/lib/embeddings.ts)
    - Expected output: 1536 dimensions
    - Base URL: Ollama instance (Docker service or localhost)
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "qwen3-embedding"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    return _embeddings_instance


async def generate_embedding(text: str) -> list[float]:
    """
    Generate a single embedding vector, with dimension validation.

    Mirrors the behavior of src/lib/embeddings.ts:generateEmbedding()
    which validates: embedding.length === 1536
    """
    embeddings = get_embeddings()
    vector = await embeddings.aembed_query(text)

    if len(vector) != EXPECTED_DIMS:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EXPECTED_DIMS}, "
            f"got {len(vector)}. Check EMBEDDING_MODEL configuration."
        )

    return vector


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in one call."""
    embeddings = get_embeddings()
    vectors = await embeddings.aembed_documents(texts)

    for i, v in enumerate(vectors):
        if len(v) != EXPECTED_DIMS:
            raise ValueError(
                f"Embedding dimension mismatch at index {i}: "
                f"expected {EXPECTED_DIMS}, got {len(v)}"
            )

    return vectors
