import pickle
import os
import bm25s

# Path to your BM25 index - UPDATE THIS IF NEEDED
bm25_path = "bm25_index.pkl"

def run_debug():
    if not os.path.exists(bm25_path):
        print(f"❌ BM25 index file not found at: {os.path.abspath(bm25_path)}")
        return

    with open(bm25_path, "rb") as f:
        data = pickle.load(f)
    
    print(f"✅ BM25 pickle loaded successfully")
    print(f"  - Keys in data: {list(data.keys())}")
    
    corpus = data.get('corpus', [])
    print(f"  - Corpus type: {type(corpus)}")
    print(f"  - Corpus length: {len(corpus)}")
    
    if corpus and len(corpus) > 0:
        print(f"  - First item: {str(corpus[0])[:100]}...")
    
    retriever = data.get("retriever")
    if retriever:
        print(f"  - Retriever type: {type(retriever)}")
        
        # Test Search
        try:
            retriever.corpus = corpus
            tokenized_query = bm25s.tokenize(["test"])
            # Some bm25s versions need the index to be initialized
            results = retriever.retrieve(tokenized_query, k=1)
            print(f"  - Test search worked! Found {len(results.documents[0])} docs.")
        except Exception as e:
            print(f"  - Test search failed: {e}")

if __name__ == "__main__":
    run_debug()