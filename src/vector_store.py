"""
Vector store abstraction for RAG and semantic search.

Uses Chroma when available (Python < 3.14). Falls back to a simple
JSON+numpy store on Python 3.14 or when Chroma fails (e.g. Pydantic compatibility).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

RAG_COLLECTION_NAME = "mises_rag"

# Filenames for simple backend
_CHUNKS_JSON = "chunks.json"
_EMBEDDINGS_NPY = "embeddings.npy"


class SimpleVectorStore:
    """
    File-based vector store: chunks in JSON, embeddings in .npy.
    No Chroma dependency; works on Python 3.14+.
    """

    def __init__(self, persist_directory: Path):
        self._dir = Path(persist_directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._chunks_path = self._dir / _CHUNKS_JSON
        self._embeddings_path = self._dir / _EMBEDDINGS_NPY
        self._chunks: List[Dict[str, Any]] = []
        self._embeddings: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self._id_to_idx: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if self._chunks_path.exists():
            try:
                with open(self._chunks_path, "r", encoding="utf-8") as f:
                    self._chunks = json.load(f)
            except Exception as e:
                logger.warning("Could not load chunks.json: %s", e)
                self._chunks = []
        else:
            self._chunks = []
        if self._embeddings_path.exists():
            try:
                self._embeddings = np.load(self._embeddings_path)
            except Exception as e:
                logger.warning("Could not load embeddings.npy: %s", e)
                self._embeddings = np.zeros((0, 0), dtype=np.float32)
        else:
            self._embeddings = np.zeros((0, 0), dtype=np.float32)
        self._id_to_idx = {c["id"]: i for i, c in enumerate(self._chunks)}

    def _save(self) -> None:
        with open(self._chunks_path, "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False, indent=0)
        np.save(self._embeddings_path, self._embeddings)

    def add(
        self,
        chunk_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta = dict(metadata or {})
        for k, v in list(meta.items()):
            if v is None:
                del meta[k]
            elif not isinstance(v, (str, int, float, bool)):
                meta[k] = str(v)
        vec = np.array(embedding, dtype=np.float32)
        if chunk_id in self._id_to_idx:
            i = self._id_to_idx[chunk_id]
            self._chunks[i] = {"id": chunk_id, "text": text, "metadata": meta}
            self._embeddings[i] = vec
        else:
            self._id_to_idx[chunk_id] = len(self._chunks)
            self._chunks.append({"id": chunk_id, "text": text, "metadata": meta})
            if self._embeddings.shape[0] == 0:
                self._embeddings = vec.reshape(1, -1)
            else:
                self._embeddings = np.vstack([self._embeddings, vec])
        self._save()

    def search(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self._embeddings.shape[0] == 0:
            return []
        q = np.array(embedding, dtype=np.float32).reshape(1, -1)
        # Cosine similarity: dot / (norm * norm). Chroma uses distance = 1 - similarity for cosine.
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        sim = (self._embeddings @ q.T).ravel() / (norms.ravel() * np.linalg.norm(q))
        # Filter by metadata
        indices = np.arange(len(self._chunks))
        if filter_metadata:
            for k, v in filter_metadata.items():
                if v is None:
                    continue
                mask = np.array([
                    self._chunks[i].get("metadata", {}).get(k) == v
                    for i in range(len(self._chunks))
                ])
                indices = indices[mask]
                if len(indices) == 0:
                    return []
        if len(indices) == 0:
            return []
        sim_sub = np.array([sim[i] for i in indices])
        top = np.argsort(-sim_sub)[:top_k]
        # Chroma returns distance; we use 1 - similarity so lower distance = more similar
        out: List[Dict[str, Any]] = []
        for pos in top:
            i = indices[pos]
            sim_val = float(sim_sub[pos])
            out.append({
                "id": self._chunks[i]["id"],
                "text": self._chunks[i]["text"],
                "metadata": self._chunks[i].get("metadata", {}),
                "distance": 1.0 - sim_val,
            })
        return out

    def delete_by_source(self, source: str) -> None:
        keep = [c for c in self._chunks if c.get("metadata", {}).get("source") != source]
        self._replace_chunks(keep)

    def delete_by_type(self, type_value: str) -> None:
        keep = [c for c in self._chunks if c.get("metadata", {}).get("type") != type_value]
        self._replace_chunks(keep)

    def _replace_chunks(self, keep: List[Dict[str, Any]]) -> None:
        if not keep:
            self._chunks = []
            self._embeddings = np.zeros((0, 0), dtype=np.float32)
            self._id_to_idx = {}
        else:
            keep_ids = {c["id"] for c in keep}
            keep_indices = [i for i, c in enumerate(self._chunks) if c["id"] in keep_ids]
            self._chunks = keep
            self._embeddings = self._embeddings[keep_indices]
            self._id_to_idx = {c["id"]: i for i, c in enumerate(self._chunks)}
        self._save()
        logger.info("Store now has %d chunks", len(self._chunks))

    def count(self) -> int:
        return len(self._chunks)


class ChromaVectorStore:
    """Chroma-backed vector store (fails on Python 3.14 due to Pydantic v1)."""

    def __init__(self, persist_directory: Path):
        import chromadb
        from chromadb.config import Settings
        persist_directory = Path(persist_directory)
        persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=RAG_COLLECTION_NAME,
            metadata={"description": "RAG chunks for Mises Data Curator"},
        )

    def add(
        self,
        chunk_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        meta = dict(metadata or {})
        for k, v in list(meta.items()):
            if v is None:
                del meta[k]
            elif not isinstance(v, (str, int, float, bool)):
                meta[k] = str(v)
        self._collection.upsert(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[meta],
        )

    def search(
        self,
        embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        where = None
        if filter_metadata:
            where = {k: v for k, v in filter_metadata.items() if v is not None}
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: List[Dict[str, Any]] = []
        ids = result["ids"][0] if result["ids"] else []
        docs = result["documents"][0] if result["documents"] else []
        metadatas = result["metadatas"][0] if result["metadatas"] else []
        distances = result["distances"][0] if result.get("distances") else []
        for i, cid in enumerate(ids):
            out.append({
                "id": cid,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else None,
            })
        return out

    def delete_by_source(self, source: str) -> None:
        try:
            self._collection.delete(where={"source": source})
            logger.info("Deleted chunks with source=%s", source)
        except Exception as e:
            logger.warning("delete_by_source(%s) failed: %s", source, e)

    def delete_by_type(self, type_value: str) -> None:
        try:
            self._collection.delete(where={"type": type_value})
            logger.info("Deleted chunks with type=%s", type_value)
        except Exception as e:
            logger.warning("delete_by_type(%s) failed: %s", type_value, e)

    def count(self) -> int:
        return self._collection.count()


def VectorStore(persist_directory: Path):
    """
    Factory: returns Chroma-backed store if available, otherwise SimpleVectorStore.
    Use SimpleVectorStore on Python 3.14+ when Chroma fails (Pydantic v1).
    """
    try:
        return ChromaVectorStore(persist_directory)
    except Exception as e:
        logger.warning("Chroma not available (%s), using simple file-based vector store", e)
        return SimpleVectorStore(persist_directory)
