"""RAG (retrieval-augmented generation) and vector indexation for AI Ready."""

from .index import build_index, chunk_docs, chunk_catalog, chunk_tools

__all__ = ["build_index", "chunk_docs", "chunk_catalog", "chunk_tools"]
