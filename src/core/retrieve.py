import bm25s
import pickle
import os
import hashlib
import logging
import time
import numpy as np
from typing import List, Tuple, Optional
from langchain_core.documents import Document
from .config_service import ConfigManager
from .hybrid_search_config import HybridSearchConfig, fuse_hybrid_scores
from .reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)

# --- STRICT OFFLINE ---
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Lazy global variables
_reranker = None

def get_low_confidence_threshold():
    """Lazily fetches the threshold from config."""
    return ConfigManager.get("LOW_CONFIDENCE_THRESHOLD", 50.0)

def get_reranker():
    """Lazily loads the reranker only when needed."""
    global _reranker
    if _reranker is None:
        logger.info(f"🎯 Loading Reranker...")
        _reranker = CrossEncoderReranker()
    return _reranker


def _normalize_vector_scores(scores, method='minmax'):
    """Normalize L2 distances to [0, 1] range (lower distance = higher relevance)."""
    scores = np.array(scores)
    if method == 'minmax':
        min_s, max_s = scores.min(), scores.max()
        if max_s > min_s:
            normalized = 1 - (scores - min_s) / (max_s - min_s)
        else:
            normalized = np.ones_like(scores)
    return normalized


def _normalize_bm25_scores(scores, method='minmax'):
    """Normalize BM25 scores to [0, 1] range."""
    scores = np.array(scores)
    if method == 'minmax':
        min_s, max_s = scores.min(), scores.max()
        if max_s > min_s:
            normalized = (scores - min_s) / (max_s - min_s)
        else:
            normalized = np.ones_like(scores)
    return normalized


def _fuse_hybrid_scores(vector_scores, bm25_scores, alpha=0.6):
    """Fuse normalized scores from both retrieval methods."""
    v_norm = _normalize_vector_scores(vector_scores)
    b_norm = _normalize_bm25_scores(bm25_scores)
    return alpha * v_norm + (1 - alpha) * b_norm


# ============ DEDUPLICATION HELPERS ============

def get_document_id(doc) -> str:
    """Create a unique identifier for a document using metadata."""
    source = doc.metadata.get("source", "unknown")
    page = doc.metadata.get("page", None)
    
    if page is not None:
        return f"{source}:{int(page)}"
    else:
        content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()[:8]
        return f"{source}:{content_hash}"


def deduplicate_documents(docs: List[Document], strategy: str = 'metadata') -> List[Document]:
    """
    Deduplicate documents efficiently.
    
    Args:
        docs: List of Document objects
        strategy: 'metadata' (fastest) or 'content' (more accurate)
    
    Returns:
        List of unique documents
    """
    if not docs:
        return []
    
    if strategy == 'metadata':
        seen_ids = set()
        unique_docs = []
        duplicates_found = 0
        
        for doc in docs:
            doc_id = get_document_id(doc)
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(doc)
            else:
                duplicates_found += 1
        
        if duplicates_found > 0:
            logger.debug(f"Dedup: Found {duplicates_found} duplicates")
        
        return unique_docs
    
    elif strategy == 'content':
        seen_hashes = set()
        unique_docs = []
        duplicates_found = 0
        
        for doc in docs:
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_docs.append(doc)
            else:
                duplicates_found += 1
        
        if duplicates_found > 0:
            logger.debug(f"Dedup: Found {duplicates_found} content duplicates")
        
        return unique_docs
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def get_dynamic_rerank_limit(top_score: float, base_limit: int = 5) -> int:
    """Adaptively determine rerank limit based on confidence."""
    if top_score > 0.85:
        return max(3, base_limit // 2)
    elif top_score > 0.70:
        return base_limit
    else:
        return base_limit * 2


def load_bm25(path):
    """Loads the BM25 index and re-syncs the corpus with re-indexing."""
    with open(path, "rb") as f:
        data = pickle.load(f)
    
    retriever = data["retriever"]
    retriever.corpus = data["corpus"]
    
    # Re-index the corpus to ensure the retriever's internal state is valid
    if retriever.corpus and len(retriever.corpus) > 0:
        tokenized_corpus = bm25s.tokenize(retriever.corpus)
        retriever.index(tokenized_corpus)
        logger.debug(f"✅ BM25 retriever re-indexed with {len(retriever.corpus)} documents")
    
    return retriever


# ============ BM25 DOCUMENT EXTRACTION ============

def _extract_bm25_documents(bm25_results, bm25_retriever) -> List[Document]:
    """Safely extract documents from BM25 results."""
    docs = []
    
    try:
        if not hasattr(bm25_results, 'documents') or bm25_results.documents is None:
            logger.debug("BM25 returned no documents")
            return docs
        
        doc_indices = bm25_results.documents
        if doc_indices is None:
            doc_indices = []
        elif isinstance(doc_indices, np.ndarray):
            doc_indices = doc_indices.flatten().tolist()
        elif isinstance(doc_indices, (list, tuple)) and len(doc_indices) == 1 and isinstance(doc_indices[0], (list, tuple, np.ndarray)):
            doc_indices = list(doc_indices[0])
        elif isinstance(doc_indices, (list, tuple)):
            doc_indices = list(doc_indices)
        else:
            doc_indices = list(doc_indices)
        
        if len(doc_indices) == 0:
            logger.debug("BM25 document indices are empty")
            return docs
        
        if isinstance(doc_indices, np.ndarray):
            doc_indices = doc_indices.flatten().tolist()
        elif not isinstance(doc_indices, (list, tuple)):
            doc_indices = list(doc_indices)
        
        corpus = bm25_retriever.corpus if hasattr(bm25_retriever, 'corpus') and bm25_retriever.corpus is not None else []
        
        for idx in doc_indices:
            try:
                idx = int(idx)
                if 0 <= idx < len(corpus):
                    doc_text = corpus[idx]
                    
                    if isinstance(doc_text, str):
                        docs.append(Document(
                            page_content=doc_text,
                            metadata={"source": "bm25_search", "rerank_score": 0.0}
                        ))
                    elif hasattr(doc_text, 'page_content'):
                        docs.append(doc_text)
                    else:
                        logger.warning(f"Unknown BM25 result type: {type(doc_text)}")
            except Exception as e:
                logger.debug(f"Failed to process BM25 index {idx}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"BM25 extraction failed: {e}")
    
    return docs


# ============ SINGLE QUERY SEARCH ============

def search_single_query(query, db, bm25_retriever, k=3) -> Tuple[List[Document], list, list, int]:
    """Search using both vector and BM25 with error handling and return scores for fusion."""
    try:
        docs = []
        vector_scores = []
        bm25_scores = []
        
        # Try vector search
        try:
            docs_with_scores = db.similarity_search_with_score(query, k=k)
            for doc, score in docs_with_scores:
                doc.metadata["vector_score"] = float(score)
                docs.append(doc)
                vector_scores.append(float(score))
            
            logger.debug(f"Vector search: {len(docs_with_scores)} docs")
        except Exception as e:
            logger.warning(f"Vector search failed for '{query}': {e}")
        
        # Try BM25 search
        try:
            # Defensive: ensure BM25 retriever has corpus and is indexed
            if not hasattr(bm25_retriever, 'corpus') or bm25_retriever.corpus is None:
                logger.warning("⚠️ BM25 retriever missing corpus, attempting to restore...")
                logger.debug("BM25 search: 0 docs (corpus missing)")
            else:
                # Re-index to ensure the retriever's internal state is valid
                if len(bm25_retriever.corpus) > 0:
                    tokenized_corpus = bm25s.tokenize(bm25_retriever.corpus)
                    bm25_retriever.index(tokenized_corpus)
            
            query_tokens = bm25s.tokenize([query])
            bm25_results = bm25_retriever.retrieve(
                query_tokens, k=k, return_as="tuple", show_progress=False
            )
            
            logger.debug(f"BM25 raw results: documents={bm25_results.documents is not None}, scores={bm25_results.scores is not None}")
            
            bm25_doc_indices = bm25_results.documents
            bm25_doc_scores = bm25_results.scores

            if bm25_doc_indices is None:
                bm25_doc_indices = []
            elif isinstance(bm25_doc_indices, np.ndarray):
                bm25_doc_indices = bm25_doc_indices.flatten().tolist()
            elif isinstance(bm25_doc_indices, (list, tuple)) and len(bm25_doc_indices) == 1 and isinstance(bm25_doc_indices[0], (list, tuple, np.ndarray)):
                bm25_doc_indices = list(bm25_doc_indices[0])
            elif isinstance(bm25_doc_indices, (list, tuple)):
                bm25_doc_indices = list(bm25_doc_indices)
            else:
                bm25_doc_indices = list(bm25_doc_indices)

            if bm25_doc_scores is None:
                bm25_doc_scores = []
            elif isinstance(bm25_doc_scores, np.ndarray):
                bm25_doc_scores = bm25_doc_scores.flatten().tolist()
            elif isinstance(bm25_doc_scores, (list, tuple)) and len(bm25_doc_scores) == 1 and isinstance(bm25_doc_scores[0], (list, tuple, np.ndarray)):
                bm25_doc_scores = list(bm25_doc_scores[0])
            elif isinstance(bm25_doc_scores, (list, tuple)):
                bm25_doc_scores = list(bm25_doc_scores)
            else:
                bm25_doc_scores = list(bm25_doc_scores)

            if len(bm25_doc_indices) == 0:
                logger.debug("BM25 returned no document indices")
                bm25_doc_scores = []

            corpus = bm25_retriever.corpus if hasattr(bm25_retriever, 'corpus') and bm25_retriever.corpus is not None else []
            logger.debug(f"BM25: {len(bm25_doc_indices)} indices, {len(corpus)} corpus items, {len(bm25_doc_scores)} scores")
            
            for idx, score in zip(bm25_doc_indices, bm25_doc_scores):
                try:
                    # Handle case where idx might already be a Document or string
                    if isinstance(idx, str):
                        # idx is actually document text, not an index
                        logger.debug(f"BM25 returning document text directly (type: str)")
                        doc = Document(
                            page_content=idx,
                            metadata={"source": "bm25_search", "bm25_score": float(score)}
                        )
                        docs.append(doc)
                        bm25_scores.append(float(score))
                    else:
                        # idx should be an integer
                        idx = int(idx)
                        if 0 <= idx < len(corpus):
                            doc_text = corpus[idx]
                            if isinstance(doc_text, str):
                                doc = Document(
                                    page_content=doc_text,
                                    metadata={"source": "bm25_search", "bm25_score": float(score)}
                                )
                            elif hasattr(doc_text, 'page_content'):
                                doc = doc_text
                                doc.metadata["bm25_score"] = float(score)
                            else:
                                logger.warning(f"Unknown BM25 result type: {type(doc_text)}")
                                continue
                            docs.append(doc)
                            bm25_scores.append(float(score))
                except ValueError as e:
                    logger.debug(f"Failed to convert BM25 index to int (got type {type(idx).__name__}): {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Failed to process BM25 result at index {idx}: {e}")
                    continue
            
            logger.debug(f"BM25 search: {len(bm25_scores)} docs (out of {len(bm25_doc_indices)} results)")
        except Exception as e:
            logger.warning(f"BM25 search failed for '{query}': {e}")
        
        if not docs:
            logger.warning(f"No results from either search method for: {query}")
        
        return docs, vector_scores, bm25_scores, len(docs)
    
    except Exception as e:
        logger.error(f"search_single_query failed: {e}", exc_info=True)
        return [], [], [], 0


# ============ HYBRID SEARCH ============

def _perform_hybrid_search(query, db, bm25_retriever, k=60, rerank_limit=5, extra_queries=None, reranker=None):
    """
    Core hybrid search orchestration logic shared by multiple interfaces.
    
    Args:
        query: Main query string
        db: FAISS vector store
        bm25_retriever: BM25 retriever instance
        k: Number of results to retrieve per query
        rerank_limit: Top K results after reranking
        extra_queries: Additional queries for multi-query search
        reranker: Pre-loaded CrossEncoder reranker (lazy loads if None)
    
    Returns:
        (documents, low_confidence, confidence_pct)
    """
    overall_start = time.time()
    config = HybridSearchConfig()
    
    try:
        all_queries = [query] + (extra_queries or [])
        doc_map = {}
        
        logger.debug(f"Searching {len(all_queries)} queries with k={k} and RRF k={config.rrf_k}...")
        
        # Search with all queries
        for i, q in enumerate(all_queries, 1):
            try:
                t_start = time.time()
                docs, _, _, _ = search_single_query(q, db, bm25_retriever, k=k)
                elapsed = time.time() - t_start
                logger.debug(f"  Query {i}/{len(all_queries)}: {len(docs)} docs in {elapsed:.3f}s")
                for doc in docs:
                    doc_id = get_document_id(doc)
                    existing = doc_map.get(doc_id)
                    if existing is None:
                        doc_map[doc_id] = doc
                    else:
                        for score_key in ("vector_score", "bm25_score"):
                            if score_key in doc.metadata and doc.metadata[score_key] is not None:
                                existing.metadata[score_key] = doc.metadata[score_key]
            except Exception as e:
                logger.error(f"Query '{q}' failed: {e}")
                continue
        
        unique_docs = list(doc_map.values())
        if not unique_docs:
            logger.warning(f"No documents retrieved for: {query}")
            return [], True, 0
        
        # Deduplicate with timing
        try:
            t_start = time.time()
            unique_docs = deduplicate_documents(unique_docs, strategy='metadata')
            elapsed = time.time() - t_start
            logger.debug(f"Dedup: {len(doc_map)} → {len(unique_docs)} unique in {elapsed:.3f}s")
            
            # DEBUG: Log what we found
            if not unique_docs:
                logger.warning(f"⚠️ No documents found for query: '{query}'")
                logger.warning(f"⚠️ This suggests: (1) Data folder may be empty, (2) BM25 index is broken, or (3) No matching documents")
            else:
                sources_found = set()
                for doc in unique_docs[:5]:
                    sources_found.add(doc.metadata.get("source", "unknown"))
                logger.debug(f"Sources found: {sources_found}")
        except Exception as e:
            logger.error(f"Deduplication failed: {e}, using all docs")
        
        # Prepare hybrid ranking scores
        vector_scores = np.array([doc.metadata.get("vector_score", np.nan) for doc in unique_docs], dtype=float)
        bm25_scores = np.array([doc.metadata.get("bm25_score", np.nan) for doc in unique_docs], dtype=float)
        
        if np.isnan(vector_scores).any():
            replacement = np.nanmax(vector_scores) if not np.isnan(vector_scores).all() else 0.0
            vector_scores = np.nan_to_num(vector_scores, nan=replacement + 1.0)
        if np.isnan(bm25_scores).any():
            replacement = np.nanmin(bm25_scores) if not np.isnan(bm25_scores).all() else 0.0
            bm25_scores = np.nan_to_num(bm25_scores, nan=replacement - 1.0)
        
        fused_scores = fuse_hybrid_scores(vector_scores.tolist(), bm25_scores.tolist(), config)
        ranked_indices = np.argsort(-fused_scores)
        ranked_docs = [unique_docs[i] for i in ranked_indices]
        for doc, score in zip(ranked_docs, fused_scores[ranked_indices]):
            doc.metadata["hybrid_score"] = float(score)
        
        candidate_docs = ranked_docs[: max(k, rerank_limit * 3)]
        
        # Rerank with provided or lazy-loaded reranker
        try:
            if reranker is None:
                reranker = get_reranker()
            
            t_start = time.time()
            final_docs = reranker.rerank(query, candidate_docs, top_k=rerank_limit)
            elapsed = time.time() - t_start
            logger.info(f"Reranking: {len(candidate_docs)} docs → {len(final_docs)} in {elapsed:.3f}s")
            
            confidence_pct = 0
            low_confidence = True
            if final_docs:
                top_score = final_docs[0].metadata.get("rerank_score", 0.0)
                # BGE reranker outputs scores typically in range [0, 1]
                # Convert to confidence percentage: 0.5 = 50%, 0.7 = 70%, etc.
                confidence_pct = min(max(int(top_score * 100), 0), 100)
                threshold = get_low_confidence_threshold()
                low_confidence = confidence_pct < threshold
                
                # Log detailed confidence info for debugging
                logger.debug(f"Top rerank score: {top_score:.4f} → Confidence: {confidence_pct}% | Threshold: {threshold}%")
                if low_confidence:
                    logger.warning(f"⚠️ Low confidence retrieval! Top score: {top_score:.4f} | Query: '{query[:50]}...'")
            
            total = time.time() - overall_start
            logger.info(f"Hybrid search TOTAL: {total:.3f}s | Confidence: {confidence_pct}%")
            return final_docs, low_confidence, confidence_pct
        except Exception as e:
            logger.warning(f"Reranking failed: {e}, falling back to hybrid ranked results")
            logger.info(f"Falling back to hybrid ranked results: {len(candidate_docs)} docs")
            fallback_docs = candidate_docs[:rerank_limit]
            return fallback_docs, True, 0
    
    except Exception as e:
        logger.error(f"Hybrid search failed completely: {e}", exc_info=True)
        return [], True, 0


def get_hybrid_docs(query, db, bm25_retriever, k=15, rerank_limit=5, extra_queries=None):
    """
    Hybrid search with graceful degradation and error recovery.
    
    DEPRECATED: Use retrieval_service.search() for new code.
    This function is kept for backward compatibility.
    """
    docs, low_conf, conf_pct = _perform_hybrid_search(
        query, db, bm25_retriever, k=k, rerank_limit=rerank_limit, 
        extra_queries=extra_queries, reranker=None
    )
    # Return format for backward compatibility (originally returned documents, low_conf, count)
    return docs, 0, 0


# ============ HEALTH CHECK ============

def health_check(brain) -> dict:
    """Check if all components are working."""
    logger.info("Running health check...")
    
    status = {
        "vector_store": False,
        "bm25_retriever": False,
        "reranker": False,
        "overall": False,
        "errors": []
    }
    
    try:
        if brain.vector_store:
            status["vector_store"] = True
            logger.info("✓ Vector store OK")
        else:
            status["errors"].append("Vector store not loaded")
    except Exception as e:
        status["errors"].append(f"Vector store error: {e}")
    
    try:
        if brain.bm25_retriever:
            status["bm25_retriever"] = True
            logger.info("✓ BM25 OK")
        else:
            status["errors"].append("BM25 not loaded")
    except Exception as e:
        status["errors"].append(f"BM25 error: {e}")
    
    try:
        reranker = get_reranker()
        if reranker:
            status["reranker"] = True
            logger.info("✓ Reranker OK")
        else:
            status["errors"].append("Reranker not loaded")
    except Exception as e:
        status["errors"].append(f"Reranker error: {e}")
    
    status["overall"] = all([
        status["vector_store"],
        status["bm25_retriever"],
        status["reranker"]
    ])
    
    if status["overall"]:
        logger.info("✅ All systems healthy")
    else:
        logger.error(f"❌ Health check failed: {status['errors']}")
    
    return status
