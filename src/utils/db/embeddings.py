"""
=============================================================================
EMBEDDINGS - AgentEmbedder (ollama SDK with Matryoshka dimensions)
=============================================================================

Shared embedding generation using ollama.AsyncClient directly, with the
``dimensions`` parameter on every API call.  This ensures Ollama truncates
and renormalizes Matryoshka-capable models (e.g. qwen3-embedding) server-side
so that query vectors always match the pgvector column width.

The LangChain OllamaEmbeddings wrapper does not yet support the
``dimensions`` kwarg (langchain#34623), so we bypass it and implement the
langchain_core.embeddings.Embeddings interface ourselves.

Pattern origin: mirrors src/pipeline/embedder.py (proven in production).

=============================================================================
"""

import asyncio
import os
from typing import List

import ollama
from langchain_core.embeddings import Embeddings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EMBEDDING_DIMS = int(os.getenv("EMBEDDING_DIMS", "1536"))
SUB_BATCH_SIZE = 10  # Texts per Ollama API call (prevents timeouts)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_embedder_instance: "AgentEmbedder | None" = None


class AgentEmbedder(Embeddings):
    """
    LangChain-compatible embedder backed by ``ollama.AsyncClient``.

    Every call to the Ollama ``/api/embed`` endpoint includes
    ``dimensions=<configured>``, so the server truncates + renormalizes
    the raw model output to the requested width.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model = model or os.getenv("EMBEDDING_MODEL", "qwen3-embedding")
        self.dimensions = dimensions or EMBEDDING_DIMS
        self._client = ollama.AsyncClient(
            host=base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        self._validated = False  # first-call dimension check

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------
    async def embed(self, text: str) -> List[float]:
        """Generate a single embedding, passing ``dimensions`` to Ollama."""
        response = await self._client.embed(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
        )
        vector = response["embeddings"][0]
        self._validate_once(vector)
        return vector

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for *texts*, sub-batched to avoid timeouts.

        Each sub-batch is a single ``/api/embed`` call with up to
        ``SUB_BATCH_SIZE`` inputs.
        """
        all_vectors: List[List[float]] = []
        for start in range(0, len(texts), SUB_BATCH_SIZE):
            chunk = texts[start : start + SUB_BATCH_SIZE]
            response = await self._client.embed(
                model=self.model,
                input=chunk,
                dimensions=self.dimensions,
            )
            vectors = response["embeddings"]
            if not self._validated and vectors:
                self._validate_once(vectors[0])
            all_vectors.extend(vectors)
        return all_vectors

    # ------------------------------------------------------------------
    # LangChain Embeddings interface
    # ------------------------------------------------------------------
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Sync wrapper required by LangChain Embeddings."""
        return asyncio.get_event_loop().run_until_complete(
            self.aembed_documents(texts)
        )

    def embed_query(self, text: str) -> List[float]:
        """Sync wrapper required by LangChain Embeddings."""
        return asyncio.get_event_loop().run_until_complete(
            self.aembed_query(text)
        )

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async batch embedding (LangChain interface)."""
        return await self.embed_batch(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """Async single-query embedding (LangChain interface)."""
        return await self.embed(text)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def embedding_dimension(self) -> int:
        """Return the configured embedding dimension."""
        return self.dimensions

    def _validate_once(self, vector: List[float]) -> None:
        """Check the first response matches the configured dimension."""
        if self._validated:
            return
        if len(vector) != self.dimensions:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimensions}, "
                f"got {len(vector)}. Check EMBEDDING_DIMS / EMBEDDING_MODEL "
                f"configuration."
            )
        self._validated = True


# ---------------------------------------------------------------------------
# Module-level convenience API (public surface — same signatures as before)
# ---------------------------------------------------------------------------

def get_embedder() -> AgentEmbedder:
    """Return the shared AgentEmbedder singleton."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = AgentEmbedder()
    return _embedder_instance


# Backwards-compatible alias so existing ``from utils.db import get_embeddings``
# continues to work without import changes.
get_embeddings = get_embedder


async def generate_embedding(text: str) -> List[float]:
    """
    Generate a single embedding vector (1536-d by default).

    Drop-in replacement for the previous OllamaEmbeddings-based function.
    """
    return await get_embedder().embed(text)


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts, sub-batched at 10 per call."""
    return await get_embedder().embed_batch(texts)
