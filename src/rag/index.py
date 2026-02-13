"""
RAG indexation: chunk docs, catalog, and tools; embed and store in vector store.

Run via CLI: python -m src.cli rag-index (or curate rag-index).
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Chunk size and overlap for fixed-window chunking
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


def chunk_text_by_sections(text: str, source_path: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Split markdown by ## headers. Each section becomes one chunk.
    Returns list of (chunk_text, metadata).
    """
    sections = re.split(r"\n(?=##\s)", text)
    out: List[Tuple[str, Dict[str, Any]]] = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 20:
            continue
        # If section is too long, split by fixed window
        if len(section) > CHUNK_SIZE:
            for j, start in enumerate(range(0, len(section), CHUNK_SIZE - CHUNK_OVERLAP)):
                sub = section[start : start + CHUNK_SIZE]
                if len(sub.strip()) < 30:
                    continue
                out.append((sub, {"source": source_path, "type": "doc", "section": j}))
        else:
            out.append((section, {"source": source_path, "type": "doc"}))
    return out


def chunk_text_fixed(text: str, source_path: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Split text into fixed-size windows with overlap. Fallback when no headers."""
    out: List[Tuple[str, Dict[str, Any]]] = []
    for start in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
        sub = text[start : start + CHUNK_SIZE].strip()
        if len(sub) < 30:
            continue
        out.append((sub, {"source": source_path, "type": "doc"}))
    return out


def chunk_docs(docs_root: Path) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Load all .md under docs_root and chunk by sections (or fixed window).
    Returns list of (text, metadata) with type=doc, source=file path.
    """
    chunks: List[Tuple[str, Dict[str, Any]]] = []
    if not docs_root.exists():
        return chunks
    for path in sorted(docs_root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Skip %s: %s", path, e)
            continue
        try:
            source_path = str(path.relative_to(docs_root))
        except ValueError:
            source_path = path.name
        if "## " in text:
            chunks.extend(chunk_text_by_sections(text, source_path))
        else:
            chunks.extend(chunk_text_fixed(text, source_path))
    return chunks


def _dataset_to_text(dataset: Dict[str, Any]) -> str:
    """Build searchable text for one dataset (catalog metadata)."""
    parts = []
    parts.append(dataset.get("indicator_name") or dataset.get("name", ""))
    parts.append(dataset.get("description", ""))
    if dataset.get("topic"):
        parts.append(f"Topic: {dataset['topic']}")
    if dataset.get("source"):
        parts.append(f"Source: {dataset['source']}")
    cols = dataset.get("columns") or []
    if cols:
        parts.append("Columns: " + ", ".join(c if isinstance(c, str) else c.get("name", "") for c in cols[:20]))
    countries = dataset.get("countries") or []
    if countries and len(countries) <= 30:
        parts.append("Countries: " + ", ".join(str(c) for c in countries[:30]))
    elif countries:
        parts.append(f"Countries: {len(countries)} countries")
    return " | ".join(p for p in parts if p)


def chunk_catalog(catalog) -> List[Tuple[str, Dict[str, Any]]]:
    """
    One chunk per dataset from DatasetCatalog. Uses search(limit=5000) to list all.
    Returns list of (text, metadata) with type=catalog, dataset_id, source=catalog.
    """
    chunks: List[Tuple[str, Dict[str, Any]]] = []
    try:
        datasets = catalog.search(query="", limit=5000)
    except Exception as e:
        logger.warning("Catalog search failed: %s", e)
        return chunks
    for ds in datasets:
        text = _dataset_to_text(ds)
        if not text.strip():
            continue
        meta = {"source": "catalog", "type": "catalog", "dataset_id": ds.get("id")}
        chunks.append((text, meta))
    return chunks


def chunk_tools() -> List[Tuple[str, Dict[str, Any]]]:
    """
    One chunk per MCP tool: name + docstring. Metadata type=tool, source=tool name.
    """
    chunks: List[Tuple[str, Dict[str, Any]]] = []
    try:
        from src import copilot_tools
        tool_list = copilot_tools.list_tools()
        for name in tool_list:
            info = copilot_tools.get_tool(name)
            if not info:
                continue
            desc = info.get("description") or ""
            text = f"Tool: {name}\n{desc}"
            meta = {"source": name, "type": "tool"}
            chunks.append((text, meta))
    except Exception as e:
        logger.warning("chunk_tools failed: %s", e)
    return chunks


def _chunk_id(prefix: str, content: str, index: int) -> str:
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"{prefix}_{index}_{h}"


def build_index(
    config: Any,
    docs_root: Optional[Path] = None,
    index_docs: bool = True,
    index_catalog: bool = True,
    index_tools: bool = True,
) -> Dict[str, int]:
    """
    Build or rebuild the RAG vector index.

    Args:
        config: Config instance (for data_root, get_rag_config not required for store path)
        docs_root: Root for .md files (default: project root / docs)
        index_docs: Index docs/*.md
        index_catalog: Index DatasetCatalog metadata
        index_tools: Index MCP tool descriptions

    Returns:
        Dict with counts: docs, catalog, tools.
    """
    from src.embeddings import get_embedding_provider
    from src.vector_store import VectorStore

    rag_cfg = config.get_rag_config()
    persist_dir = rag_cfg["chroma_persist_dir"]
    provider_name = rag_cfg.get("embedding_provider", "openai")
    provider = get_embedding_provider(
        provider_name,
        model=rag_cfg.get("embedding_model"),
        base_url=rag_cfg.get("embedding_base_url"),
    )
    store = VectorStore(persist_dir)

    if docs_root is None:
        docs_root = Path(config.data_root) / "docs"
    if not docs_root.is_absolute():
        docs_root = Path(config.data_root) / docs_root

    counts = {"docs": 0, "catalog": 0, "tools": 0}

    if index_docs:
        store.delete_by_type("doc")
        doc_chunks = chunk_docs(docs_root)
        if not doc_chunks:
            logger.info("No doc chunks under %s", docs_root)
        else:
            texts = [t for t, _ in doc_chunks]
            embeddings = provider.embed_batch(texts)
            for i, ((text, meta), emb) in enumerate(zip(doc_chunks, embeddings)):
                cid = _chunk_id("doc", text, i)
                store.add(cid, text, emb, meta)
            counts["docs"] = len(doc_chunks)
            logger.info("Indexed %d doc chunks", len(doc_chunks))

    if index_catalog:
        store.delete_by_source("catalog")
        from src.dataset_catalog import DatasetCatalog
        catalog = DatasetCatalog(config)
        catalog_chunks = chunk_catalog(catalog)
        if catalog_chunks:
            texts = [t for t, _ in catalog_chunks]
            embeddings = provider.embed_batch(texts)
            for i, ((text, meta), emb) in enumerate(zip(catalog_chunks, embeddings)):
                cid = _chunk_id("catalog", text, i)
                store.add(cid, text, emb, meta)
            counts["catalog"] = len(catalog_chunks)
            logger.info("Indexed %d catalog chunks", len(catalog_chunks))

    if index_tools:
        store.delete_by_type("tool")
        tool_chunks = chunk_tools()
        if tool_chunks:
            texts = [t for t, _ in tool_chunks]
            embeddings = provider.embed_batch(texts)
            for i, ((text, meta), emb) in enumerate(zip(tool_chunks, embeddings)):
                cid = _chunk_id("tool", text, i)
                store.add(cid, text, emb, meta)
            counts["tools"] = len(tool_chunks)
            logger.info("Indexed %d tool chunks", len(tool_chunks))

    return counts
