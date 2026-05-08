"""
reranker.py — Abstract interface for reranking models.

Provides a unified interface for different reranking backends.
Currently implements CrossEncoder, but allows for alternative rerankers.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import List, Tuple
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from .config_service import ConfigManager

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """Abstract base class for reranking models."""
    
    @abstractmethod
    def rerank(self, query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: Query string
            documents: Documents to rerank
            top_k: Number of top results to return
        
        Returns:
            Reranked documents with scores in metadata
        """
        pass


class CrossEncoderReranker(Reranker):
    """Reranker implementation using sentence-transformers CrossEncoder."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize CrossEncoder reranker.
        
        Args:
            model_path: Path to reranker model. If None, loads from config.
        """
        if model_path is None:
            model_path = self._get_reranker_path()
        
        logger.info(f"⏳ Loading CrossEncoder reranker from: {model_path}")
        
        try:
            self.model = CrossEncoder(model_path, device='cpu')
            logger.info(f"✅ CrossEncoder reranker loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load CrossEncoder: {e}")
            raise
    
    @staticmethod
    def _get_reranker_path() -> str:
        """Get reranker path from config."""
        rel_path = ConfigManager.get("RERANKER_PATH", "model/bge-reranker-v2-m3")
        return os.path.join(ConfigManager.PROJECT_ROOT, rel_path)
    
    def rerank(self, query: str, documents: List[Document], top_k: int = 5, batch_size: int = 32) -> List[Document]:
        """
        Rerank documents using CrossEncoder.
        
        Args:
            query: Query string
            documents: Documents to rerank
            top_k: Number of top results to return
            batch_size: Batch size for inference
        
        Returns:
            Top-k reranked documents with scores
        """
        if not documents:
            return []
        
        import numpy as np
        
        doc_texts = [d.page_content for d in documents]
        
        # Batch inference
        all_scores = []
        for i in range(0, len(doc_texts), batch_size):
            batch_pairs = [[query, text] for text in doc_texts[i:i+batch_size]]
            batch_scores = self.model.predict(batch_pairs)
            
            if isinstance(batch_scores, np.ndarray):
                batch_scores = batch_scores.flatten().tolist()
            elif not isinstance(batch_scores, (list, tuple)):
                batch_scores = [batch_scores]
            
            all_scores.extend(batch_scores)
        
        # Sort by score
        ranked = sorted(zip(all_scores, documents), key=lambda x: float(x[0]), reverse=True)
        
        # Return top-k with scores in metadata
        final_docs = []
        for score, doc in ranked[:top_k]:
            try:
                score_float = float(score)
            except (ValueError, TypeError):
                score_float = 0.0
            
            doc.metadata["rerank_score"] = score_float
            final_docs.append(doc)
        
        return final_docs


def get_reranker(reranker_class: type = CrossEncoderReranker, model_path: str = None) -> Reranker:
    """
    Factory function to create a reranker instance.
    
    Args:
        reranker_class: Class to instantiate (must implement Reranker interface)
        model_path: Optional path to model
    
    Returns:
        Reranker instance
    """
    return reranker_class(model_path=model_path)
