# Integration Guide: Using the New RAG Features

Complete guide on how to integrate and use the three new RAG features.

---

## Feature 1: Chat History Memory for RAG Context

The `chat_store.py` already persists conversations. Now `conversation_context.py` adds intelligence to use that history for better searches.

### Quick Start

```python
from conversation_context import integrate_conversation_context
from brain_service import Brain

brain = Brain()
brain.load()

# Get user query and session ID (from your chat interface)
user_query = "Tell me more about that"
session_id = 123  # From your chat UI

# Enhance query with conversation context
context_info = integrate_conversation_context(user_query, session_id)

# Use the enhanced query for RAG search
docs, low_conf, conf_pct = brain.search(context_info["enhanced_query"])

print(f"Context Type: {context_info['context_type']}")  # 'follow-up', 'new-topic', or 'standalone'
print(f"Session Summary: {context_info['session_summary']}")
```

### What It Does

- Detects follow-up questions vs. new topics
- Extracts entities and main topics from conversation
- Enhances queries with relevant context
- Provides conversation summaries for inclusion in LLM prompts

### Integration with app.py

```python
from conversation_context import integrate_conversation_context

# In your chat message handler:
if session_id:
    context_info = integrate_conversation_context(user_input, session_id)
    enhanced_query = context_info["enhanced_query"]
    session_summary = context_info["session_summary"]
else:
    enhanced_query = user_input
    session_summary = ""

# Pass enhanced_query to brain.search()
docs, low_conf, conf_pct = brain.search(enhanced_query)

# Optionally include session_summary in your LLM prompt for better context awareness
prompt = f"""
Based on this conversation context:
{session_summary}

Please answer: {user_input}

Using these documents:
{formatted_docs}
"""
```

---

## Feature 2: Configurable Hybrid Search with RRF

Replace the simple weighted average fusion with Reciprocal Rank Fusion for better handling of outliers and diverse result types.

### Quick Start

```python
from hybrid_search_config import (
    get_default_config,
    get_semantic_config,
    get_keyword_config,
    get_balanced_config
)

# Use pre-configured profiles:
config = get_semantic_config()  # 70% vector, 30% BM25, RRF enabled

# Or customize:
config = get_default_config()
config.vector_weight = 0.55
config.bm25_weight = 0.45
config.use_rrf = True
config.rrf_k = 60
config.rerank_top_k = 5
```

### Available Profiles

| Profile | Vector | BM25 | Best For |
|---------|--------|------|----------|
| `get_default_config()` | 60% | 40% | Balanced, general use |
| `get_semantic_config()` | 70% | 30% | Semantic matching, QA |
| `get_keyword_config()` | 30% | 70% | Technical docs, keywords |
| `get_balanced_config()` | 50% | 50% | Uncertain, mixed content |

### Why RRF is Better

- ✓ More robust to outlier scores
- ✓ Handles diverse document types better
- ✓ Stable across different query types
- ✓ Configurable via rrf_k parameter

### Integration with retrieve.py

```python
from hybrid_search_config import get_semantic_config

def get_hybrid_docs(query, db, bm25_retriever, k=15, rerank_limit=5, extra_queries=None):
    # Use semantic config for better retrieval
    config = get_semantic_config()

    all_queries = [query] + (extra_queries or [])
    all_docs = []

    for q in all_queries:
        docs, scores_vector, scores_bm25 = search_single_query(q, db, bm25_retriever, k=k)

        # Use RRF fusion instead of simple weighted average
        fused_scores = fuse_hybrid_scores_rrf(scores_vector, scores_bm25, config)
        # ... sort and rerank ...
```

### Tuning Parameters

```python
config = get_default_config()

# How much to trust vector search
config.vector_weight = 0.6  # 0.0-1.0

# How much to trust BM25 search
config.bm25_weight = 0.4  # 0.0-1.0

# Use Reciprocal Rank Fusion
config.use_rrf = True  # Better than simple weighted average

# RRF constant (lower = more aggressive ranking)
config.rrf_k = 60  # Try 40-100

# How many results to rerank
config.rerank_top_k = 5

# Enable cross-encoder reranking
config.enable_reranking = True

# BM25 tuning
config.bm25_k1 = 1.5  # Term frequency saturation
config.bm25_b = 0.75  # Length normalization
```

---

## Feature 3: Faithfulness Checking

Automatically evaluate whether generated answers are grounded in source documents, detecting hallucinations and unsupported claims.

### Quick Start

```python
from faithfulness_check import evaluate_answer_faithfulness

# After generating an answer with RAG
answer = "The company was founded in 1995..."
documents = [doc1, doc2, doc3]  # Retrieved documents

# Evaluate faithfulness
result = evaluate_answer_faithfulness(answer, documents)

print(f"Faithfulness Score: {result['overall_score']:.2f}")
print(f"Confidence Level: {result['confidence_level']}")
print(f"Is Faithful: {result['is_faithful']}")
print(f"Concerns: {result['concerns']}")

# Component scores for debugging:
print(result['component_scores'])
```

### Output Interpretation

**overall_score** (0.0-1.0): How faithful the answer is to sources
- 0.9-1.0: Excellent, fully grounded
- 0.75-0.9: Good, minor issues
- 0.6-0.75: Acceptable, some concerns
- < 0.6: Poor, likely hallucinations

**is_faithful**: Boolean (True if score > 0.7) for easy filtering

**confidence_level**: Human-readable assessment

**component_scores**: Breakdown for diagnosis
- **token_overlap**: What % of answer tokens appear in docs
- **semantic_consistency**: How similar answer is to doc meaning
- **entity_grounding**: What % of key entities are in docs
- **contradiction**: Flags negation inconsistencies

**concerns**: List of specific issues found

### Output Example

```json
{
  "overall_score": 0.87,
  "is_faithful": true,
  "confidence_level": "High",
  "component_scores": {
    "token_overlap": 0.85,
    "semantic_consistency": 0.92,
    "entity_grounding": 0.78,
    "contradiction": 1.0
  },
  "concerns": [
    "Low token overlap with some documents"
  ],
  "evidence_count": 3
}
```

### Integration with generate_evals.py

Already integrated! The evaluation script now outputs faithfulness scores:

```bash
python generate_evals.py --dataset test --sample 5
```

Output includes:
```
🔍 Faithfulness: High (0.87)
```

### Use in Your App

```python
from faithfulness_check import evaluate_answer_faithfulness
from generate import answer_question

# In your answer generation pipeline:
answer, sources = answer_question(user_query, retrieved_docs)

# Check faithfulness
faith_result = evaluate_answer_faithfulness(answer, retrieved_docs)

# Show user a confidence indicator
if faith_result['is_faithful']:
    confidence_badge = "✓ High Confidence"
else:
    confidence_badge = "⚠️ Low Confidence - verify with sources"

print(f"{answer}\n{confidence_badge}")

# Optionally re-retrieve if confidence is too low
if faith_result['overall_score'] < 0.6:
    print("Re-retrieving additional documents...")
    # Get more documents and regenerate answer
```

---

## Complete Integration Example

```python
from brain_service import Brain
from conversation_context import integrate_conversation_context
from hybrid_search_config import get_semantic_config
from faithfulness_check import evaluate_answer_faithfulness
from generate import answer_question

# Setup
brain = Brain()
brain.load()

# User sends multi-turn message
user_query = "What about the recent changes?"
session_id = 123

# 1. Enhance with conversation context
print("📝 Processing conversation context...")
ctx_info = integrate_conversation_context(user_query, session_id)
print(f"   Context Type: {ctx_info['context_type']}")
print(f"   Enhanced Query: {ctx_info['enhanced_query']}")

# 2. Search with intelligent hybrid fusion
print("🔍 Searching with hybrid retrieval...")
config = get_semantic_config()  # 70% vector, 30% BM25
docs = brain.search(ctx_info["enhanced_query"], config=config)

# 3. Generate answer
print("💡 Generating answer...")
answer, sources = answer_question(user_query, docs)

# 4. Check faithfulness
print("✅ Checking faithfulness...")
faith = evaluate_answer_faithfulness(answer, docs)

# Display results
print("\n" + "="*60)
print(answer)
print(f"\nConfidence: {faith['confidence_level']} ({faith['overall_score']:.2%})")
if not faith['is_faithful']:
    print(f"⚠️ Issues: {', '.join(faith['concerns'])}")
print("="*60)
```

---

## Performance Guidelines

| Feature | Latency | Memory | When to Use |
|---------|---------|--------|-------------|
| Conversation Context | < 5ms | Low | Always (for multi-turn) |
| Hybrid Search RRF | < 1ms | Low | Always (better than simple avg) |
| Faithfulness Check | 100-500ms | Medium | QA evaluation, not real-time |

---

## Troubleshooting

### Conversation context not improving results

Check:
1. Session ID is correct
2. Session has previous messages stored
3. Database connection is working
4. Entity extraction is working (check logs)

### RRF results worse than before

Try:
1. `get_keyword_config()` if documents are keyword-heavy
2. Adjust `rrf_k` parameter (lower = more aggressive)
3. Verify BM25 index is properly built
4. Check if `enable_reranking=True` helps

### Faithfulness scores too low

Check:
1. Retrieved documents are actually relevant
2. Documents contain the answer information
3. Token overlap score - may need more sources
4. Look at component_scores to identify specific problem

