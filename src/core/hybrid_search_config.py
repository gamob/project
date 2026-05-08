"""
hybrid_search_config.py — Advanced hybrid search with configurable RRF parameters.

Implements multiple fusion strategies:
1. Simple weighted average (alpha-based)
2. Reciprocal Rank Fusion (RRF) - more robust to outliers
3. Cross-encoder reranking for final refinement

Configurable parameters allow tuning for different data types and use cases.
"""

from typing import List, Tuple, Dict
import numpy as np
from langchain_core.documents import Document


class HybridSearchConfig:
    """Configuration for hybrid search fusion strategies."""
    
    def __init__(self):
        """Initialize with sensible defaults."""
        # Weighted average fusion
        self.vector_weight = 0.6      # 60% vector, 40% BM25
        self.bm25_weight = 0.4
        
        # RRF (Reciprocal Rank Fusion) parameters
        self.rrf_k = 60               # Constant to prevent division by zero
        self.use_rrf = True           # Use RRF by default (more robust)
        
        # BM25-specific tuning
        self.bm25_k1 = 1.5            # Controls term saturation (default is 1.5)
        self.bm25_b = 0.75            # Controls length normalization (0-1)
        
        # Reranking
        self.enable_reranking = True
        self.rerank_top_k = 5
        self.rerank_batch_size = 32
        
        # Confidence thresholds
        self.min_vector_score = 0.3   # Skip if below this
        self.min_bm25_score = 0.1     # Skip if below this
    
    def to_dict(self) -> Dict:
        """Serialize configuration."""
        return {
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight,
            "rrf_k": self.rrf_k,
            "use_rrf": self.use_rrf,
            "bm25_k1": self.bm25_k1,
            "bm25_b": self.bm25_b,
            "enable_reranking": self.enable_reranking,
            "rerank_top_k": self.rerank_top_k,
            "rerank_batch_size": self.rerank_batch_size,
            "min_vector_score": self.min_vector_score,
            "min_bm25_score": self.min_bm25_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "HybridSearchConfig":
        """Deserialize configuration."""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


def reciprocal_rank_fusion(vector_ranks: np.ndarray, bm25_ranks: np.ndarray, 
                           k: float = 60.0) -> np.ndarray:
    """
    Reciprocal Rank Fusion: Combines rankings from multiple retrieval methods.
    
    Formula: RRF(d) = Σ 1 / (k + rank(d))
    
    Args:
        vector_ranks: Rank positions from vector search (0-indexed)
        bm25_ranks: Rank positions from BM25 search (0-indexed)
        k: Constant to prevent division by zero (default 60)
    
    Returns:
        Fused scores for each document
    """
    # Convert to numpy arrays if needed
    vector_ranks = np.asarray(vector_ranks, dtype=float)
    bm25_ranks = np.asarray(bm25_ranks, dtype=float)
    
    # Calculate RRF scores: 1 / (k + rank)
    vector_rrf = 1.0 / (k + vector_ranks + 1)
    bm25_rrf = 1.0 / (k + bm25_ranks + 1)
    
    # Average the RRF scores
    fused = (vector_rrf + bm25_rrf) / 2.0
    
    return fused


def normalize_vector_scores(scores: List[float]) -> np.ndarray:
    """Normalize L2 distances to [0, 1] range (lower distance = higher relevance)."""
    scores = np.asarray(scores, dtype=float)
    if len(scores) == 0:
        return np.array([])
    
    min_s, max_s = scores.min(), scores.max()
    if max_s > min_s:
        normalized = 1 - (scores - min_s) / (max_s - min_s)
    else:
        normalized = np.ones_like(scores)
    
    return normalized


def normalize_bm25_scores(scores: List[float]) -> np.ndarray:
    """Normalize BM25 scores to [0, 1] range."""
    scores = np.asarray(scores, dtype=float)
    if len(scores) == 0:
        return np.array([])
    
    min_s, max_s = scores.min(), scores.max()
    if max_s > min_s:
        normalized = (scores - min_s) / (max_s - min_s)
    else:
        normalized = np.ones_like(scores)
    
    return normalized


def fuse_hybrid_scores_weighted(vector_scores: List[float], 
                               bm25_scores: List[float],
                               config: HybridSearchConfig) -> np.ndarray:
    """
    Fuse scores using weighted average method.
    
    Args:
        vector_scores: L2 distances from FAISS
        bm25_scores: Relevance scores from BM25
        config: HybridSearchConfig object
    
    Returns:
        Fused scores array
    """
    v_norm = normalize_vector_scores(vector_scores)
    b_norm = normalize_bm25_scores(bm25_scores)
    
    fused = config.vector_weight * v_norm + config.bm25_weight * b_norm
    return fused


def fuse_hybrid_scores_rrf(vector_scores: List[float],
                          bm25_scores: List[float],
                          config: HybridSearchConfig) -> np.ndarray:
    """
    Fuse scores using Reciprocal Rank Fusion (more robust to outliers).
    
    Args:
        vector_scores: L2 distances from FAISS
        bm25_scores: Relevance scores from BM25
        config: HybridSearchConfig object
    
    Returns:
        Fused scores array
    """
    # Sort to get ranks
    vector_scores_arr = np.asarray(vector_scores, dtype=float)
    bm25_scores_arr = np.asarray(bm25_scores, dtype=float)
    
    # Get rank positions (argsort returns indices, we invert because
    # vector search: lower L2 distance = higher rank
    # bm25 search: higher score = higher rank)
    vector_ranks = np.argsort(np.argsort(vector_scores_arr))  # Lower scores = higher rank
    bm25_ranks = np.argsort(np.argsort(-bm25_scores_arr))     # Higher scores = higher rank
    
    # Apply RRF
    fused = reciprocal_rank_fusion(vector_ranks, bm25_ranks, config.rrf_k)
    
    return fused


def fuse_hybrid_scores(vector_scores: List[float],
                      bm25_scores: List[float],
                      config: HybridSearchConfig = None) -> np.ndarray:
    """
    Smart hybrid score fusion using configured strategy.
    
    Args:
        vector_scores: L2 distances from FAISS
        bm25_scores: Relevance scores from BM25
        config: HybridSearchConfig (uses defaults if None)
    
    Returns:
        Fused scores array
    """
    if config is None:
        config = HybridSearchConfig()
    
    if config.use_rrf:
        return fuse_hybrid_scores_rrf(vector_scores, bm25_scores, config)
    else:
        return fuse_hybrid_scores_weighted(vector_scores, bm25_scores, config)


def get_default_config() -> HybridSearchConfig:
    """Get default hybrid search configuration."""
    return HybridSearchConfig()


def get_balanced_config() -> HybridSearchConfig:
    """Configuration for balanced retrieval (50/50 vector and BM25)."""
    config = HybridSearchConfig()
    config.vector_weight = 0.5
    config.bm25_weight = 0.5
    return config


def get_semantic_config() -> HybridSearchConfig:
    """Configuration emphasizing semantic similarity (70% vector, 30% BM25)."""
    config = HybridSearchConfig()
    config.vector_weight = 0.7
    config.bm25_weight = 0.3
    config.rrf_k = 50  # Lower k for more aggressive RRF
    return config


def get_keyword_config() -> HybridSearchConfig:
    """Configuration emphasizing keyword matching (30% vector, 70% BM25)."""
    config = HybridSearchConfig()
    config.vector_weight = 0.3
    config.bm25_weight = 0.7
    config.rrf_k = 80  # Higher k for gentler RRF
    return config
