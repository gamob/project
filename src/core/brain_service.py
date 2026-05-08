import os
import json
import hashlib
import shutil
import logging
import time
import pickle
from .config_service import ConfigManager
from .index_service import IndexService
from .retrieval_service import get_retrieval_service
from ..data.load_data import load_documents, load_specific_files
from ..data.split_text import split_docs
from .generate import generate_search_queries

logger = logging.getLogger(__name__)


class Brain:
    """The central Service that manages the AI's memory and retrieval."""
    
    def __init__(self):
        self.faiss_path = os.path.join(
            ConfigManager.PROJECT_ROOT,
            ConfigManager.get("FAISS_INDEX_PATH", "faiss_index")
        )
        self.bm25_path = os.path.join(
            ConfigManager.PROJECT_ROOT,
            ConfigManager.get("BM25_INDEX_PATH", "bm25_index.pkl")
        )
        self.data_dir = os.path.join(
            ConfigManager.PROJECT_ROOT,
            ConfigManager.get("DATA_DIR", "data")
        )
        self.state_path = os.path.join(ConfigManager.PROJECT_ROOT, "index_state.json")

        self.vector_store = None
        self.bm25_retriever = None
        self.bm25_data = None
        
        # Get the retrieval service (reranker already loaded)
        self.retrieval_service = get_retrieval_service()
        
        # Cache for file modification times (faster than hashing)
        self._file_mtime_cache = {}

    def _get_file_hash(self, filepath):
        """
        Generates an MD5 hash of a file's content.
        
        Optimized: First checks file modification time to avoid unnecessary hashing.
        """
        try:
            current_mtime = os.path.getmtime(filepath)
            cached_mtime = self._file_mtime_cache.get(filepath)
            
            # If mtime hasn't changed, return cached hash
            if cached_mtime is not None and cached_mtime == current_mtime:
                # Return a consistent hash based on filepath + mtime
                return hashlib.md5(f"{filepath}:{current_mtime}".encode()).hexdigest()
            
            # Otherwise, compute full hash and cache mtime
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            hash_result = hasher.hexdigest()
            self._file_mtime_cache[filepath] = current_mtime
            return hash_result
        
        except (OSError, IOError) as e:
            logger.error(f"❌ Failed to hash file {filepath}: {e}")
            raise

    def _get_old_index_paths(self):
        """Get the old index paths for migration (before moving out of src folder)."""
        old_faiss = os.path.join(os.path.dirname(self.faiss_path), "src", os.path.basename(self.faiss_path))
        old_bm25 = os.path.join(os.path.dirname(self.bm25_path), "src", os.path.basename(self.bm25_path))
        return old_faiss, old_bm25

    def _old_indices_exist(self):
        """Check if indices exist in old location."""
        old_faiss, old_bm25 = self._get_old_index_paths()
        return os.path.exists(old_faiss) and os.path.exists(old_bm25)

    def _migrate_indices_from_old_location(self):
        """Migrate indices from old location (src/) to new location."""
        old_faiss, old_bm25 = self._get_old_index_paths()
        
        if not self._old_indices_exist():
            return
        
        logger.info("🔄 Migrating indices from old location to new location...")
        if os.path.exists(old_faiss):
            shutil.copytree(old_faiss, self.faiss_path, dirs_exist_ok=True)
        if os.path.exists(old_bm25):
            shutil.copy2(old_bm25, self.bm25_path)

    def _load_state(self):
        """Load index state from current or old location."""
        state = {}
        
        if os.path.exists(self.state_path):
            with open(self.state_path, 'r') as f:
                state = json.load(f)
        else:
            old_state_path = os.path.join(os.path.dirname(self.state_path), "src", "index_state.json")
            if os.path.exists(old_state_path):
                logger.info("🔄 Found state file in old location, will migrate...")
                with open(old_state_path, 'r') as f:
                    state = json.load(f)
        
        return state

    def is_built(self):
        """Checks if both indices exist on disk."""
        if os.path.exists(self.faiss_path) and os.path.exists(self.bm25_path):
            return True

        if self._old_indices_exist():
            logger.info("🔄 Found indices in old location, will migrate to new location...")
            return True

        return False

    def load(self):
        """Loads indices into memory."""
        if not self.is_built():
            raise FileNotFoundError("Indices are missing. Need to build the brain first.")

        logger.info("🧠 Waking up the brain indices...")

        # Migrate from old location if needed
        self._migrate_indices_from_old_location()

        # Load indices through IndexService
        self.vector_store, self.bm25_data = IndexService.load_existing_indices()
        self.bm25_retriever = self.bm25_data["retriever"]

        # Connect indices to retrieval service
        self.retrieval_service.set_indices(self.vector_store, self.bm25_retriever)

        logger.info("✅ Brain is fully loaded and ready!")

    def build(self, chunks=None):
        """Builds a fresh brain."""
        
        if chunks is None:
            logger.info("🧠 No chunks provided, loading fresh from data folder...")
            raw_docs = load_documents(self.data_dir)
            chunks = split_docs(raw_docs)
        
        if os.path.exists(self.faiss_path):
            shutil.rmtree(self.faiss_path)
        
        # Create indices through IndexService
        self.vector_store, self.bm25_data = IndexService.create_fresh_indices(chunks)
        self.bm25_retriever = self.bm25_data["retriever"]

        logger.info("✅ Brain rebuild complete!")

    def _compute_file_hashes_and_detect_changes(self, old_state):
        """
        Scan data directory, compute file hashes, and detect new/changed files.
        
        Returns:
            (new_or_changed_files: List[str], new_state: Dict[str, str])
        """
        all_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(self.data_dir) for f in filenames]
        new_or_changed_files = []
        new_state = {}

        for file_path in all_files:
            relative_path = os.path.relpath(file_path, ConfigManager.PROJECT_ROOT)
            current_hash = self._get_file_hash(file_path)
            new_state[relative_path] = current_hash
            
            # Check both relative and absolute paths for backward compatibility
            if (old_state.get(relative_path) != current_hash and 
                old_state.get(file_path) != current_hash):
                new_or_changed_files.append(file_path)
        
        return new_or_changed_files, new_state

    def _process_new_files_into_chunks(self, file_paths):
        """
        Load and process new/changed files into document chunks.
        
        Args:
            file_paths: List of file paths to process
        
        Returns:
            List of document chunks
        """
        all_chunks = []
        
        for file_path in file_paths:
            logger.info(f"  👉 Processing {os.path.basename(file_path)}...")
            t_start = time.time()
            doc = load_specific_files([file_path])
            chunks = split_docs(doc)
            elapsed = time.time() - t_start
            logger.debug(f"    Processed in {elapsed:.3f}s ({len(chunks)} chunks)")
            all_chunks.extend(chunks)
        
        return all_chunks

    def _update_indices_with_chunks(self, new_chunks):
        """
        Update indices with new chunks, either fresh build or incremental add.
        
        Args:
            new_chunks: List of new document chunks
        """
        if not self.is_built():
            # Fresh build needed
            self.build(new_chunks)
        else:
            # Incremental update
            if not self.vector_store:
                self.load()

            self.vector_store, self.bm25_data = IndexService.add_documents_incremental(
                self.vector_store, self.bm25_data, new_chunks
            )
            self.bm25_retriever = self.bm25_data["retriever"]

    def _save_state(self, state_dict):
        """Save the current state of file hashes to disk."""
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)

    def sync_indices(self):
        """Incremental Update: Only processes new/changed files."""
        logger.info("🔄 Syncing indices...")
        
        # Load state from current or old location
        old_state = self._load_state()
        
        # Detect new/changed files
        new_or_changed_files, new_state = self._compute_file_hashes_and_detect_changes(old_state)

        # Check if update is needed
        if not new_or_changed_files and self.is_built():
            logger.info("✨ Brain is already up to date!")
            if not self.vector_store: 
                self.load()
            return

        logger.info(f"✨ Processing {len(new_or_changed_files)} changes...")

        # Process new files into chunks
        new_chunks = self._process_new_files_into_chunks(new_or_changed_files)
        
        # Update indices
        self._update_indices_with_chunks(new_chunks)
        
        # Save state
        self._save_state(new_state)

        logger.info("✅ Sync complete!")

    def search(self, query: str, extra_queries=None, k: int = 20):
        """Standardized interface for searching the documents."""
        if not self.vector_store or not self.bm25_retriever:
            raise ValueError("Brain is not loaded! Call brain.sync_indices() first.")

        overall_start = time.time()
        
        try:
            # Measure query rewriting
            t_start = time.time()
            if extra_queries is None:
                main_query, extra_queries = generate_search_queries(query)
            else:
                main_query = query
            elapsed = time.time() - t_start
            logger.debug(f"generate_search_queries: {elapsed:.3f}s")

            # Use retrieval service for search
            t_start = time.time()
            docs, low_confidence, confidence_pct = self.retrieval_service.search(
                main_query,
                extra_queries=extra_queries,
                k=k,
                rerank_limit=4
            )
            elapsed = time.time() - t_start
            logger.info(f"retrieval_service.search: {elapsed:.3f}s | {len(docs)} docs | Conf: {confidence_pct}%")

            total = time.time() - overall_start
            logger.info(f"Brain.search TOTAL: {total:.3f}s")
            
            return docs, low_confidence, confidence_pct
        
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise
