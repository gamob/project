"""
main.py — Example of using the updated RAG system with all quick wins enabled.

Key changes:
1. Setup logging at startup
2. Initialize retrieval service (loads reranker once)
3. Run health check to verify everything works
4. Use brain.search() with detailed logs
"""

import logging
import sys

# Import logging configuration
from src.core.logging_config import setup_logging

# Import core components
from src.core.brain_service import Brain
from src.core.retrieval_service import initialize_retrieval_service
from src.core.retrieve import health_check
from src.core.generate import check_ollama_health


def main():
    """Main entry point for RAG system."""
    
    # 1. Set up logging (shows detailed timing info)
    logger = setup_logging(level=logging.INFO)
    logger.info("=" * 80)
    logger.info("🚀 Starting RAG System")
    logger.info("=" * 80)
    
    try:
        # 2. Check Ollama health
        logger.info("Checking Ollama server...")
        ollama_ok, ollama_msg = check_ollama_health()
        if not ollama_ok:
            logger.error(f"❌ Ollama check failed: {ollama_msg}")
            return False
        logger.info(f"✅ {ollama_msg}")
        
        # 3. Initialize retrieval service (loads reranker ONCE at startup)
        # This is Quick Win #2 - avoids 2-5 second cold start on first query
        logger.info("\nInitializing retrieval service...")
        initialize_retrieval_service()  # Takes 2-5 seconds here
        
        # 4. Create and load brain
        logger.info("\nLoading brain indices...")
        brain = Brain()
        brain.load()  # Loads FAISS + BM25 indices
        
        # 5. Run health check (Quick Win #4)
        logger.info("\nRunning health check...")
        status = health_check(brain)
        if not status["overall"]:
            logger.error("❌ Health check failed!")
            for error in status["errors"]:
                logger.error(f"  - {error}")
            return False
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ System Ready! Press Ctrl+C to exit")
        logger.info("=" * 80 + "\n")
        
        # 6. Interactive search loop
        return interactive_search(brain)
    
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        return False


def interactive_search(brain):
    """Interactive search loop with timing information."""
    logger = logging.getLogger(__name__)
    
    while True:
        try:
            query = input("\n🔍 Enter your question (or 'exit' to quit): ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                logger.info("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            # Search with detailed logging
            # Quick Win #1 - Logging shows exact timings
            logger.info(f"\nSearching for: {query}")
            docs, low_confidence, confidence = brain.search(query)
            
            # Display results
            logger.info(f"\n{'=' * 80}")
            if docs:
                logger.info(f"Found {len(docs)} documents (Confidence: {confidence}%)")
                logger.info(f"{'=' * 80}\n")
                
                # Show top result
                doc = docs[0]
                logger.info("Top Result:")
                logger.info(f"Source: {doc.metadata.get('source', 'Unknown')}")
                logger.info(f"Score: {doc.metadata.get('rerank_score', 0):.3f}")
                logger.info(f"\n{doc.page_content[:500]}...")
                logger.info("")
                
                if low_confidence:
                    logger.info("⚠️  Low confidence result - consider asking a different question")
            else:
                logger.info("❌ No documents found")
                logger.info("(Check logs to see if it was a search error or no match)")
            logger.info('=' * 80)
        
        except KeyboardInterrupt:
            logger.info("\n👋 Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error during search: {e}", exc_info=True)
            continue


def example_batch_search(brain):
    """Example of batch searching with logging."""
    logger = logging.getLogger(__name__)
    
    queries = [
        "What is RAG?",
        "How does FAISS work?",
        "What is the difference between vector and keyword search?"
    ]
    
    logger.info("Running batch search example...\n")
    
    for i, query in enumerate(queries, 1):
        logger.info(f"\n[{i}/{len(queries)}] {query}")
        try:
            docs, low_conf, conf = brain.search(query)
            logger.info(f"  → {len(docs)} docs retrieved (Conf: {conf}%)")
        except Exception as e:
            logger.error(f"  → Error: {e}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
