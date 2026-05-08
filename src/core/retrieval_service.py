"""
retrieval_service.py — Centralized service for document retrieval.

Handles:
- Loading models (reranker) once at startup (eager loading)
- Hybrid search (vector + BM25)
- Error handling with graceful degradation
"""

import logging
import time
from typing import List, Tuple, Optional
from langchain_core.documents import Document

from .reranker import CrossEncoderReranker
from .retrieve import (
    deduplicate_documents,
    get_low_confidence_threshold,
    _perform_hybrid_search
)

logger = logging.getLogger(__name__)


class RetrievalService:
    """Manages document retrieval with eager model loading."""
    
    def __init__(self):
        """Initialize retrieval service and load models at startup."""
        logger.info("🚀 Initializing RetrievalService...")
        
        # Load reranker ONCE at startup
        self.reranker = self._load_reranker()
        
        # These get set later when Brain loads
        self.vector_store = None
        self.bm25_retriever = None
        
        logger.info("✅ RetrievalService initialized")
    
    @staticmethod
    def _load_reranker():
        """Load the reranker model once at startup."""
        logger.info(f"⏳ Loading Reranker...")
        
        start = time.time()
        try:
            reranker = CrossEncoderReranker()
            elapsed = time.time() - start
            logger.info(f"✅ Reranker loaded in {elapsed:.2f}s")
            return reranker
        except Exception as e:
            logger.error(f"❌ Failed to load reranker: {e}")
            raise
    
    def set_indices(self, vector_store, bm25_retriever):
        """Called by Brain after indices are loaded."""
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        logger.info("📚 Indices connected to RetrievalService")
    
    def search(self, query: str, extra_queries: Optional[List[str]] = None,
               k: int = 20, rerank_limit: int = 5) -> Tuple[List[Document], bool, int]:
        """
        Perform hybrid search with reranking.
        
        Args:
            query: User query
            extra_queries: Additional queries for hybrid search
            k: Number of documents to retrieve
            rerank_limit: Top K after reranking
        
        Returns:
            (documents, low_confidence, confidence_pct)
        """
        if not self.vector_store or not self.bm25_retriever:
            raise ValueError("Indices not loaded! Call set_indices() first.")
        
        # Delegate to shared hybrid search implementation
        # Pass pre-loaded reranker to avoid reloading
        return _perform_hybrid_search(
            query,
            self.vector_store,
            self.bm25_retriever,
            k=k,
            rerank_limit=rerank_limit,
            extra_queries=extra_queries,
            reranker=self.reranker
        )


# Global instance (singleton pattern)
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get or create the retrieval service."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service


def initialize_retrieval_service():
    """Explicitly initialize retrieval service at app startup."""
    global _retrieval_service
    logger.info("Initializing retrieval service...")
    _retrieval_service = RetrievalService()
    logger.info("✅ Retrieval service initialized")
    return _retrieval_service
