# Quick Reference - RAG Features Developer Guide

One-page reference for the three new RAG features.

---

## 1. Chat History Memory for RAG

**File:** `src/conversation_context.py`

### Basic Usage

```python
from conversation_context import integrate_conversation_context

# In your chat handler:
info = integrate_conversation_context(user_query, session_id=chat_session_id)

# Use the enhanced query
docs = brain.search(info["enhanced_query"])
```

### Returns

```python
{
  "original_query": "the input",
  "enhanced_query": "query with context",
  "context_type": "follow-up" | "new-topic" | "standalone",
  "session_summary": "brief context"
}
```

### When To Use

- ✓ Multi-turn conversations
- ✓ When users refer back to previous messages ("Tell me more about X")
- ✓ Topic-switching scenarios
- ✗ Don't use for: Single-turn queries (no performance benefit)

### Performance

- O(1) - just database lookups

---

## 2. Hybrid Search with RRF

**File:** `src/hybrid_search_config.py`

### Basic Usage

```python
from hybrid_search_config import get_semantic_config

config = get_semantic_config()  # Pre-tuned for semantic search
# Use config in retrieve.py's fuse_hybrid_scores()
```

### Pre-Tuned Profiles

```python
get_semantic_config()    # 70% vector, 30% BM25 (general QA)
get_keyword_config()     # 30% vector, 70% BM25 (technical docs)
get_balanced_config()    # 50% vector, 50% BM25 (mixed)
get_default_config()     # 60% vector, 40% BM25 (baseline)
```

### Customization

```python
config = get_default_config()
config.vector_weight = 0.65
config.use_rrf = True
config.rrf_k = 50  # Lower = more aggressive
```

### Parameters

```
vector_weight    → Contribution of semantic search (0.0-1.0)
bm25_weight      → Contribution of keyword search (0.0-1.0)
use_rrf          → Use RRF (True) vs weighted avg (False)
rrf_k            → RRF constant (60=default, lower=more aggressive)
rerank_top_k     → Top K results to rerank (5=default)
enable_reranking → Use CrossEncoder for final refinement
```

### When To Use

- ✓ Always - better than simple weighted average
- ✓ RRF for diverse document types
- ✓ Customize per domain/dataset

### Performance

- Minimal overhead vs weighted average

---

## 3. Faithfulness Checking

**File:** `src/faithfulness_check.py`

### Basic Usage

```python
from faithfulness_check import evaluate_answer_faithfulness

score = evaluate_answer_faithfulness(answer, retrieved_documents)

if score['is_faithful']:
  print("✓ Answer is grounded in documents")
else:
  print(f"✗ Issues: {score['concerns']}")
```

### Returns

```python
{
  "overall_score": 0.87,           # 0.0-1.0
  "is_faithful": True,             # > 0.7
  "confidence_level": "High",      # Human-readable
  "component_scores": { ... },     # Breakdown
  "concerns": [ ... ]              # Specific issues
}
```

### Score Interpretation

| Score Range | Status | Meaning |
|-------------|--------|---------|
| 0.9-1.0 | Excellent | Fully grounded |
| 0.75-0.9 | Good | Minor issues |
| 0.6-0.75 | Acceptable | Some concerns |
| < 0.6 | Poor | Likely hallucinations |

### When To Use

- ✓ Quality assurance/evaluation
- ✓ Low-confidence detection
- ✓ User feedback warnings
- ✗ Real-time: Too slow for every response

### Performance

- O(answer_length) - can be slow for large answers

---

## Minimal Integration Example

```python
from brain_service import Brain
from conversation_context import integrate_conversation_context
from hybrid_search_config import get_semantic_config
from faithfulness_check import evaluate_answer_faithfulness
from generate import answer_question

# Setup
brain = Brain()
brain.load()

# User sends message
user_query = "What about the recent changes?"
session_id = 123

# 1. Enhance with context
ctx_info = integrate_conversation_context(user_query, session_id)

# 2. Search with smart fusion
config = get_semantic_config()
docs = brain.search(ctx_info["enhanced_query"])

# 3. Generate answer
answer, sources = answer_question(user_query, docs)

# 4. Check faithfulness
faith = evaluate_answer_faithfulness(answer, docs)
confidence = faith['confidence_level']

# Done!
print(answer)
print(f"Confidence: {confidence}")
```

---

## Decision Tree: Which Feature to Use?

### Conversation Context

```
Is this a follow-up question?
├─ YES → Use integrate_conversation_context()
│        to rewrite query with history
└─ NO  → Use original query directly
```

### Hybrid Search Config

```
Are you using brain.search()?
├─ YES → Always use a HybridSearchConfig
│        (RRF is better than simple weighted average)
└─ NO  → Not applicable
```

### Faithfulness Checking

```
Are you evaluating answers?
├─ YES → Use evaluate_answer_faithfulness()
│        to check grounding
└─ NO  → Not needed for real-time chat
```

---

## Debugging Guide

### Problem: Conversation context not improving queries

**Solution:**
1. Check that session_id is correct
2. Verify session has previous messages
3. Check conversation_context logs for entity extraction

### Problem: Search results still poor despite RRF

**Solution:**
1. Check if BM25 index is built
2. Try different profile: `get_keyword_config()` for docs-heavy domains
3. Lower `rrf_k` for more aggressive ranking

### Problem: Faithfulness scores too low

**Solution:**
1. Check retrieved_documents are relevant
2. Verify documents contain answer content
3. Check token overlap - may need more sources
4. Look at component_scores to identify specific issue

---

## Integration Checklist

For **app.py** chat interface:
- [ ] Import `integrate_conversation_context`
- [ ] Call it before `brain.search()`
- [ ] Use enhanced_query for search

For **retrieve.py**:
- [ ] Import `HybridSearchConfig`
- [ ] Replace hardcoded weights with config
- [ ] Use `fuse_hybrid_scores_rrf()`

For **generate_evals.py**:
- [ ] Already has faithfulness (no action needed)
- [ ] Or add to UI for real-time warnings

---

## Performance Checklist

- ✓ Conversation Context: < 5ms (always safe)
- ✓ Hybrid RRF: < 1ms (always safe)
- ⚠️ Faithfulness: 100-500ms (use sparingly)

