"""Dataset Recommendation Engine using semantic similarity.

Suggests related datasets based on:
- Semantic embeddings of dataset descriptions (via src.embeddings + optional vector store)
- Topic and source similarity
- Temporal coverage overlap
- Geographic coverage matches
- User query context

Based on AI_FEATURES_PLAN.md Feature #2: Recomendador Inteligente de Datasets Relacionados
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hashlib

from src.config import Config
from src.dataset_catalog import DatasetCatalog


class DatasetRecommender:
    """Recommends related datasets using semantic similarity."""

    def __init__(self, config: Config):
        """
        Initialize recommender.

        Args:
            config: Configuration object
        """
        self.config = config
        self.catalog = DatasetCatalog(config)
        self.cache_dir = Path(".recommendation_cache")
        self.cache_dir.mkdir(exist_ok=True)

        self._embedding_provider = None
        self._vector_store = None
        try:
            rag_cfg = config.get_rag_config()
            if rag_cfg.get("embedding_provider"):
                from src.embeddings import get_embedding_provider
                from src.vector_store import VectorStore
                self._embedding_provider = get_embedding_provider(
                    rag_cfg.get("embedding_provider", "openai"),
                    model=rag_cfg.get("embedding_model"),
                    base_url=rag_cfg.get("embedding_base_url"),
                )
                self._vector_store = VectorStore(rag_cfg["chroma_persist_dir"])
        except Exception:
            pass
    
    async def get_recommendations(
        self,
        dataset_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get dataset recommendations.

        Uses vector store when available and query is provided; otherwise
        uses embedding provider (or TF-IDF fallback) over catalog.
        """
        if not dataset_id and not query:
            raise ValueError("Must provide either dataset_id or query")

        # Fast path: query-only and vector store has catalog chunks
        if query and self._embedding_provider and self._vector_store:
            try:
                embedding = self._embedding_provider.embed(query)
                hits = self._vector_store.search(
                    embedding,
                    top_k=limit + 5,
                    filter_metadata={"type": "catalog"},
                )
                recommendations = []
                for h in hits:
                    meta = h.get("metadata") or {}
                    did = meta.get("dataset_id")
                    if did is None:
                        continue
                    ds = self.catalog.get_dataset(int(did))
                    if not ds:
                        continue
                    dist = h.get("distance")
                    # Chroma cosine distance: 0 = identical, 2 = opposite. Convert to similarity in [0,1].
                    similarity = 1.0 - (dist / 2.0) if dist is not None else 0.5
                    if similarity < min_similarity:
                        continue
                    name = ds.get("indicator_name") or ds.get("name", "")
                    recommendations.append({
                        **ds,
                        "name": name,
                        "similarity": max(0.0, min(1.0, float(similarity))),
                        "match_reasons": self._get_match_reasons(query, ds, similarity),
                    })
                recommendations.sort(key=lambda x: x["similarity"], reverse=True)
                return recommendations[:limit]
            except Exception:
                pass

        # Standard path: embed target and compare to all datasets (or vector store unavailable)
        all_datasets = self.catalog.list_datasets()
        if not all_datasets:
            return []

        if dataset_id:
            target_dataset = next((d for d in all_datasets if str(d.get("id")) == str(dataset_id)), None)
            if not target_dataset:
                raise ValueError(f"Dataset {dataset_id} not found")
            target_text = self._create_dataset_text(target_dataset)
        else:
            target_text = query

        target_embedding = await self._get_embedding(target_text)
        recommendations = []
        for dataset in all_datasets:
            if dataset_id and str(dataset.get("id")) == str(dataset_id):
                continue
            dataset_text = self._create_dataset_text(dataset)
            dataset_embedding = await self._get_embedding(dataset_text)
            similarity = self._cosine_similarity(target_embedding, dataset_embedding)
            if similarity >= min_similarity:
                name = dataset.get("indicator_name") or dataset.get("name", "")
                recommendations.append({
                    **dataset,
                    "name": name,
                    "similarity": float(similarity),
                    "match_reasons": self._get_match_reasons(target_text, dataset, similarity),
                })
        recommendations.sort(key=lambda x: x["similarity"], reverse=True)
        return recommendations[:limit]
    
    async def recommend_for_missing_data(
        self,
        country: str,
        topic: str,
        year_range: Optional[Tuple[int, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recommend datasets to fill data gaps.
        
        Args:
            country: Country name or code
            topic: Topic/indicator type
            year_range: Optional (start_year, end_year) tuple
            
        Returns:
            List of recommended datasets that might fill the gap
        """
        # Construct search query
        query = f"{topic} data for {country}"
        if year_range:
            query += f" from {year_range[0]} to {year_range[1]}"
        
        # Get recommendations
        recs = await self.get_recommendations(query=query, limit=10, min_similarity=0.3)
        
        # Filter by criteria
        filtered = []
        for rec in recs:
            # Check if it has data for the country
            # (This would require reading the actual dataset - simplified for now)
            filtered.append({
                **rec,
                "gap_filling_reason": f"May contain {topic} data for {country}"
            })
        
        return filtered
    
    async def recommend_complementary_datasets(
        self,
        dataset_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Recommend datasets that complement the given dataset.
        
        Returns datasets grouped by relationship type:
        - similar: Same topic, different source
        - contextual: Related topics (e.g., salaries → inflation, GDP)
        - temporal: Same time period, different topics
        - geographic: Same countries, different topics
        
        Args:
            dataset_id: ID of the base dataset
            
        Returns:
            Dictionary with recommendation categories
        """
        # Get base dataset
        all_datasets = self.catalog.list_datasets()
        base_dataset = next((d for d in all_datasets if d.get('id') == dataset_id), None)
        
        if not base_dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Get all recommendations
        all_recs = await self.get_recommendations(
            dataset_id=dataset_id,
            limit=20,
            min_similarity=0.3
        )
        
        # Categorize recommendations
        categorized = {
            "similar": [],
            "contextual": [],
            "temporal": [],
            "geographic": []
        }
        
        base_source = base_dataset.get('source', '').lower()
        base_topic = base_dataset.get('topic', '').lower()
        
        for rec in all_recs:
            rec_source = rec.get('source', '').lower()
            rec_topic = rec.get('topic', '').lower()
            
            # Same topic, different source
            if rec_topic == base_topic and rec_source != base_source:
                categorized['similar'].append(rec)
            # High similarity but different topic
            elif rec['similarity'] > 0.6 and rec_topic != base_topic:
                categorized['contextual'].append(rec)
            # Same time period (would need actual data to verify)
            elif rec_source == base_source:
                categorized['temporal'].append(rec)
            else:
                categorized['geographic'].append(rec)
        
        return categorized
    
    def _create_dataset_text(self, dataset: Dict[str, Any]) -> str:
        """Create searchable text representation of dataset."""
        parts = []
        name = dataset.get("indicator_name") or dataset.get("name")
        if name:
            parts.append(name)
        if dataset.get("description"):
            parts.append(dataset["description"])
        if dataset.get("topic"):
            parts.append(f"Topic: {dataset['topic']}")
        if dataset.get("source"):
            parts.append(f"Source: {dataset['source']}")
        if dataset.get("tags"):
            parts.append(f"Tags: {', '.join(dataset['tags'])}")
        return " | ".join(parts)

    async def _get_embedding(self, text: str) -> np.ndarray:
        """
        Get semantic embedding: use src.embeddings provider when available,
        else fallback to simple TF-IDF. Result is cached on disk.
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"{text_hash}.npy"
        if cache_file.exists():
            return np.load(cache_file)

        if self._embedding_provider:
            try:
                emb = self._embedding_provider.embed(text)
                vec = np.array(emb, dtype=np.float64)
                np.save(cache_file, vec)
                return vec
            except Exception:
                pass
        embedding = self._simple_embedding(text)
        np.save(cache_file, embedding)
        return embedding
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """Simple hash-based embedding fallback."""
        # Convert text to lowercase and split into words
        words = text.lower().split()
        
        # Create a simple frequency-based vector
        # This is a placeholder - in production, use proper embeddings
        vocab = [
            "inflation", "gdp", "salarios", "wages", "unemployment", "tax",
            "population", "health", "education", "economy", "trade", "debt",
            "growth", "productivity", "inequality", "poverty", "prices"
        ]
        
        vector = np.zeros(len(vocab))
        for i, term in enumerate(vocab):
            vector[i] = sum(1 for word in words if term in word)
        
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _get_match_reasons(
        self,
        query: str,
        dataset: Dict[str, Any],
        similarity: float
    ) -> List[str]:
        """Generate human-readable reasons for the match."""
        reasons = []
        
        # High similarity
        if similarity > 0.8:
            reasons.append("Highly related topic")
        elif similarity > 0.6:
            reasons.append("Related topic")
        
        # Check for keyword matches
        query_lower = query.lower()
        name = dataset.get("indicator_name") or dataset.get("name", "")
        name_lower = name.lower()
        desc_lower = dataset.get("description", "").lower()
        
        common_terms = ["inflation", "gdp", "wages", "unemployment", "tax"]
        for term in common_terms:
            if term in query_lower and (term in name_lower or term in desc_lower):
                reasons.append(f"Contains '{term}' data")
                break
        
        # Source match
        if dataset.get('source'):
            reasons.append(f"Available from {dataset['source'].upper()}")
        
        return reasons[:3]  # Max 3 reasons


# Convenience function for CLI/API
async def get_dataset_recommendations(
    config: Config,
    dataset_id: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get dataset recommendations.
    
    Args:
        config: Configuration object
        dataset_id: Dataset to find similar datasets for
        query: Text query for recommendations
        limit: Maximum number of results
        
    Returns:
        List of recommended datasets
    """
    recommender = DatasetRecommender(config)
    return await recommender.get_recommendations(
        dataset_id=dataset_id,
        query=query,
        limit=limit
    )
