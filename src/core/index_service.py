"""
index_service.py — Abstraction layer for vector and BM25 index operations.

Reduces tight coupling by providing a unified interface for index creation,
loading, and updates. Encapsulates all index-specific logic.
"""

import logging
import os
import time
from typing import List, Tuple
from langchain_core.documents import Document

from .embed_store import (
    create_vector_store,
    load_vector_store,
    build_bm25_index,
    add_documents_incremental as embed_store_add_incremental
)

logger = logging.getLogger(__name__)


class IndexService:
    """Unified interface for managing vector and BM25 indices."""
    
    @staticmethod
    def create_fresh_indices(chunks: List[Document]) -> Tuple:
        """
        Create fresh vector and BM25 indices from chunks.
        
        Args:
            chunks: List of document chunks to index
        
        Returns:
            (vector_store, bm25_data) tuple
        """
        logger.info(f"🔨 Building indices with {len(chunks)} chunks...")
        
        # Build vector store
        t_start = time.time()
        vector_store = create_vector_store(chunks)
        elapsed = time.time() - t_start
        logger.debug(f"create_vector_store: {elapsed:.3f}s")
        
        # Build BM25 index
        t_start = time.time()
        bm25_retriever = build_bm25_index(chunks)
        elapsed = time.time() - t_start
        logger.debug(f"build_bm25_index: {elapsed:.3f}s")
        
        # Load BM25 data with corpus
        import pickle
        from .config_service import ConfigManager
        bm25_path = os.path.join(
            ConfigManager.PROJECT_ROOT,
            ConfigManager.get("BM25_INDEX_PATH", "bm25_index.pkl")
        )
        
        with open(bm25_path, "rb") as f:
            bm25_data = pickle.load(f)
        
        logger.info("✅ Indices built successfully!")
        return vector_store, bm25_data
    
    @staticmethod
    def load_existing_indices() -> Tuple:
        """
        Load existing vector and BM25 indices from disk.
        
        Returns:
            (vector_store, bm25_data) tuple
        
        Raises:
            FileNotFoundError: If indices don't exist
        """
        logger.info("🧠 Loading indices from disk...")
        
        # Load vector store
        t_start = time.time()
        vector_store = load_vector_store()
        elapsed = time.time() - t_start
        logger.debug(f"load_vector_store: {elapsed:.3f}s")
        
        # Load BM25 index
        t_start = time.time()
        import pickle
        from .config_service import ConfigManager
        bm25_path = os.path.join(
            ConfigManager.PROJECT_ROOT,
            ConfigManager.get("BM25_INDEX_PATH", "bm25_index.pkl")
        )
        
        with open(bm25_path, "rb") as f:
            bm25_data = pickle.load(f)
        
        elapsed = time.time() - t_start
        logger.debug(f"load_bm25_index: {elapsed:.3f}s")
        
        logger.info("✅ Indices loaded successfully!")
        return vector_store, bm25_data
    
    @staticmethod
    def add_documents_incremental(
        vector_store,
        bm25_data,
        new_chunks: List[Document]
    ) -> Tuple:
        """
        Incrementally add new chunks to existing indices.
        
        Args:
            vector_store: Existing FAISS vector store
            bm25_data: Existing BM25 data dictionary
            new_chunks: New chunks to add
        
        Returns:
            (updated_vector_store, updated_bm25_data) tuple
        """
        logger.info(f"➕ Adding {len(new_chunks)} new chunks incrementally...")
        
        t_start = time.time()
        vector_store, bm25_data = embed_store_add_incremental(
            vector_store, bm25_data, new_chunks
        )
        elapsed = time.time() - t_start
        logger.debug(f"add_documents_incremental: {elapsed:.3f}s")
        
        logger.info("✅ Documents added successfully!")
        return vector_store, bm25_data
