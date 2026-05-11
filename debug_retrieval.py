#!/usr/bin/env python3
"""
Diagnostic script to debug the retrieval issue.
Run this on the server to understand what's happening with query rewriting and search.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.generate import (
    generate_search_queries, 
    _needs_query_rewrite,
    check_ollama_health
)
from src.core.brain_service import Brain
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_query_rewriting():
    """Test the query rewriting logic."""
    print("\n" + "="*80)
    print("TESTING QUERY REWRITING")
    print("="*80)
    
    test_queries = [
        "how to install and setup outlook",
        "outlook setup",
        "install outlook email client",
        "hi",
        "what is python?",
    ]
    
    # Check Ollama health first
    print("\n1. Checking Ollama server health...")
    is_alive, message = check_ollama_health()
    print(f"   Ollama alive: {is_alive}")
    print(f"   Message: {message}")
    
    if not is_alive:
        print("\n⚠️ WARNING: Ollama server is not running!")
        print("   Query rewriting will be skipped for all queries.")
        print("   This might explain why search results are poor.")
        return
    
    print("\n2. Testing _needs_query_rewrite() for each query...")
    for query in test_queries:
        needs_rewrite = _needs_query_rewrite(query)
        print(f"   Query: '{query}'")
        print(f"   Needs rewrite: {needs_rewrite}")
        print()
    
    print("\n3. Testing full generate_search_queries() for Outlook query...")
    query = "how to install and setup outlook"
    try:
        main_query, extra_queries = generate_search_queries(query)
        print(f"   Input: '{query}'")
        print(f"   Main query: '{main_query}'")
        print(f"   Extra queries: {extra_queries}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()


def debug_retrieval():
    """Test the actual retrieval."""
    print("\n" + "="*80)
    print("TESTING RETRIEVAL")
    print("="*80)
    
    try:
        print("\n1. Loading brain indices...")
        brain = Brain()
        if not brain.is_built():
            print("   ❌ Brain indices not found!")
            return
        
        brain.load()
        print("   ✅ Brain loaded successfully")
        
        print("\n2. Searching for 'how to install and setup outlook'...")
        query = "how to install and setup outlook"
        
        docs, low_conf, conf_pct = brain.search(query)
        
        print(f"\n   Results:")
        print(f"   - Documents found: {len(docs)}")
        print(f"   - Confidence: {conf_pct}%")
        print(f"   - Low confidence: {low_conf}")
        
        if docs:
            print(f"\n   Top 3 results:")
            for i, doc in enumerate(docs[:3], 1):
                source = doc.metadata.get("source", "Unknown")
                page = doc.metadata.get("page", "N/A")
                snippet = doc.page_content[:100].replace("\n", " ")
                print(f"   [{i}] {source} (Page {page})")
                print(f"       Snippet: {snippet}...")
                print()
        else:
            print("   ❌ No documents retrieved!")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def inspect_data_folder():
    """Inspect what documents are in the data folder."""
    print("\n" + "="*80)
    print("INSPECTING DATA FOLDER")
    print("="*80)
    
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    
    if not os.path.exists(data_dir):
        print(f"\n❌ Data folder not found: {data_dir}")
        return
    
    print(f"\nScanning {data_dir}...")
    
    files_found = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            filepath = os.path.join(root, file)
            filesize = os.path.getsize(filepath)
            rel_path = os.path.relpath(filepath, data_dir)
            files_found.append((rel_path, filesize))
    
    if not files_found:
        print("❌ No files found in data folder!")
    else:
        print(f"\nFound {len(files_found)} files:")
        for rel_path, size in sorted(files_found):
            print(f"   - {rel_path} ({size:,} bytes)")


def main():
    print("\n" + "="*80)
    print("RETRIEVAL DEBUG DIAGNOSTIC")
    print("="*80)
    print(f"Working directory: {os.getcwd()}")
    print(f"Project root: {os.path.dirname(__file__)}")
    
    inspect_data_folder()
    debug_query_rewriting()
    debug_retrieval()
    
    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80)
    print("\nPossible issues found:")
    print("1. If Ollama is not running -> Query rewriting disabled -> Poor search results")
    print("2. If 'how to install...' doesn't trigger rewrite -> Query used as-is -> May not match documents")
    print("3. If data folder doesn't contain Outlook info -> No relevant documents to retrieve")
    print("4. If confidence is very low -> Reranker score is low -> Documents are irrelevant")


if __name__ == "__main__":
    main()
