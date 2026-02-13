"""
Embedding providers for RAG and semantic search.

Supports OpenAI-compatible API and local sentence-transformers.
Provider is selected via config (rag.embedding_provider) or env EMBEDDING_PROVIDER.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Return embedding vector for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Return embedding vectors for multiple texts (e.g. for indexation)."""
        pass


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI-compatible embeddings API (OpenAI, OpenRouter, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url or os.getenv("OPENAI_BASE_URL"))
        self.model = model

    def embed(self, text: str) -> List[float]:
        resp = self.client.embeddings.create(input=[text], model=self.model)
        return resp.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # API typically allows up to 2048 inputs per request; chunk to be safe
        batch_size = 100
        out: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            resp = self.client.embeddings.create(input=chunk, model=self.model)
            out.extend([d.embedding for d in resp.data])
        return out


class SentenceTransformerEmbedding(EmbeddingProvider):
    """Local embeddings via sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]


def get_embedding_provider(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
) -> EmbeddingProvider:
    """
    Factory: return the configured embedding provider.

    Args:
        provider: "openai" or "local"
        api_key: For openai, defaults to OPENAI_API_KEY or EMBEDDING_API_KEY env
        model: Model name (openai: e.g. text-embedding-3-small; local: e.g. all-MiniLM-L6-v2)
        base_url: For openai, base URL of OpenAI-compatible API (e.g. https://almacen.digital/api/v1)

    Returns:
        EmbeddingProvider instance
    """
    if provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("EMBEDDING_API_KEY")
        if not key:
            raise ValueError(
                "OpenAI embeddings require OPENAI_API_KEY or EMBEDDING_API_KEY"
            )
        url = base_url or os.getenv("OPENAI_BASE_URL")
        return OpenAIEmbedding(
            api_key=key,
            model=model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            base_url=url,
        )
    if provider == "local":
        return SentenceTransformerEmbedding(
            model_name=model or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        )
    raise ValueError(f"Unknown embedding provider: {provider}")
