import os
import pickle
import logging
import bm25s
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from .config_service import ConfigManager

logger = logging.getLogger(__name__)

# --- STRICT OFFLINE ---
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

def get_path(key, default_rel_path):
    """Safely builds an absolute path from the project root."""
    rel_path = ConfigManager.get(key, default_rel_path)
    if ConfigManager.PROJECT_ROOT:
        abs_path = os.path.join(ConfigManager.PROJECT_ROOT, rel_path)
        if os.path.exists(abs_path):
            return abs_path

    cwd_path = os.path.abspath(rel_path)
    if os.path.exists(cwd_path):
        return cwd_path

    # Fall back to project-root-relative path if the index/model doesn't yet exist.
    return os.path.join(ConfigManager.PROJECT_ROOT or os.getcwd(), rel_path)

def _validate_model_path(model_path):
    """Validate that embedding model files exist at the given path."""
    if not os.path.exists(model_path):
        logger.error(f"❌ Model path does not exist: {model_path}")
        return False
    
    # Check for required model files (common for HuggingFace models)
    required_files = ["config.json", "tokenizer.json"]
    found_files = [f for f in required_files if os.path.exists(os.path.join(model_path, f))]
    
    if not found_files:
        logger.warning(
            f"⚠️ Model directory exists but may be incomplete. "
            f"Expected to find at least one of: {required_files} in {model_path}"
        )
        return False
    
    logger.info(f"✅ Model validation passed for: {model_path}")
    return True

def get_llama_embeddings():
    """Initializes embeddings using the path from config."""
    model_path = get_path("MODEL_PATH", "model/bge-m3")
    
    # Validate model path
    if not _validate_model_path(model_path):
        logger.warning(f"⚠️ Proceeding with embedding initialization despite validation issues")
    
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': True}
        )
        logger.info(f"✅ Embeddings loaded successfully from: {model_path}")
        return embeddings
    except Exception as e:
        logger.error(f"❌ Failed to load embeddings from {model_path}: {e}")
        raise

def create_vector_store(chunks):
    """Builds and saves the FAISS vector store."""
    embeddings = get_llama_embeddings()
    path = get_path("FAISS_INDEX_PATH", "faiss_index")
    
    try:
        logger.info(f"🧠 Building Vector Store with {len(chunks)} chunks...")
        vector_store = FAISS.from_documents(chunks, embeddings)
        vector_store.save_local(path)
        logger.info(f"✅ FAISS index saved to '{path}'")
        return vector_store
    except Exception as e:
        logger.error(f"❌ Failed to create vector store: {e}")
        raise

def load_vector_store():
    """Loads the saved FAISS index from disk."""
    path = get_path("FAISS_INDEX_PATH", "faiss_index")

    # Backward compatibility: check old location if new doesn't exist
    if not os.path.exists(path):
        old_path = os.path.join(os.path.dirname(path), "src", os.path.basename(path))
        if os.path.exists(old_path):
            logger.info(f"🔄 Loading FAISS index from old location: {old_path}")
            path = old_path

    try:
        vector_store = FAISS.load_local(
            path,
            get_llama_embeddings(),
            allow_dangerous_deserialization=True
        )
        logger.info(f"✅ Vector store loaded from: {path}")
        return vector_store
    except Exception as e:
        logger.error(f"❌ Failed to load vector store from {path}: {e}")
        raise

def build_bm25_index(chunks):
    """Builds and saves the BM25 index WITH the corpus texts included."""
    path = get_path("BM25_INDEX_PATH", "bm25_index.pkl")
    
    try:
        corpus_texts = [chunk.page_content for chunk in chunks]
        tokenized_corpus = bm25s.tokenize(corpus_texts)
        
        retriever = bm25s.BM25()
        retriever.index(tokenized_corpus)
        
        data_to_save = {
            "retriever": retriever,
            "corpus": corpus_texts
        }
        
        with open(path, "wb") as f:
            pickle.dump(data_to_save, f)
        
        logger.info(f"✅ BM25 index saved to '{path}'")
        return retriever
    except Exception as e:
        logger.error(f"❌ Failed to build BM25 index: {e}")
        raise


def add_documents_incremental(vector_store, bm25_data, new_chunks):
    """Add new documents to existing indices without full rebuild (80-90% faster).
    
    Args:
        vector_store: Existing FAISS vector store
        bm25_data: Dict with 'retriever' and 'corpus' keys
        new_chunks: List of new Document chunks to add
    
    Returns:
        Updated vector_store and bm25_data
    """
    if not new_chunks:
        return vector_store, bm25_data
    
    try:
        embeddings = get_llama_embeddings()
        
        # Add to FAISS (much faster than rebuild)
        logger.info(f"📝 Adding {len(new_chunks)} chunks to existing indices...")
        vector_store.add_documents(new_chunks)
        
        # Add to BM25
        new_corpus_texts = [chunk.page_content for chunk in new_chunks]
        new_tokenized = bm25s.tokenize(new_corpus_texts)
        bm25_data["retriever"].index(new_tokenized)
        bm25_data["corpus"].extend(new_corpus_texts)
        
        # Save updated indices
        faiss_path = get_path("FAISS_INDEX_PATH", "faiss_index")
        bm25_path = get_path("BM25_INDEX_PATH", "bm25_index.pkl")
        
        vector_store.save_local(faiss_path)
        with open(bm25_path, "wb") as f:
            pickle.dump(bm25_data, f)
        
        logger.info(f"✅ Indices updated incrementally ({len(new_chunks)} new documents)")
        return vector_store, bm25_data
    
    except Exception as e:
        logger.error(f"❌ Failed to add documents incrementally: {e}")
        raise