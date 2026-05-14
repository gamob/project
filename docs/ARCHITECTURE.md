# Project Architecture Overview

Complete system architecture and design of the Corporate Brain RAG system.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  src/ui/app.py (Streamlit Web UI)                          │ │
│  │  src/ui/app_terminal.py (CLI Terminal UI)                  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│                    Brain Service Layer                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  src/core/brain_service.py (Orchestrator)                  │ │
│  │  - Index lifecycle management                              │ │
│  │  - High-level search orchestration                         │ │
│  │  - Session management                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────────┘
                   │
      ┌────────────┼────────────┬─────────────────┐
      │            │            │                 │
┌─────▼──┐  ┌─────▼──┐  ┌──────▼──┐  ┌──────────▼─┐
│Context │  │ Hybrid │  │Generate │  │ Reranking  │
│Manager │  │ Search │  │  & LLM  │  │ & Check    │
└────┬───┘  └────┬───┘  └───┬─────┘  └──────┬─────┘
     │           │          │               │
     │      ┌────┴─────┐    │               │
     │      │          │    │               │
┌────▼─┐ ┌──▼───┐ ┌────▼─┐ ┌▼───────┐
│Chat  │ │ VEC  │ │ BM25 │ │Reranker│
│Store │ │SEARCH│ │INDEX │ │ &Check │
└──────┘ └──────┘ └──────┘ └────────┘

Storage Layer: SQLite, FAISS, BM25 Index
```

---

## Core Components

### 1. Brain Service (Orchestrator)

**File:** `src/core/brain_service.py`

Centralized orchestrator managing the entire RAG workflow.

**Responsibilities:**
- Load and build indices
- Route search requests
- Manage concurrent access
- Handle incremental updates

**Key Methods:**
- `load()` - Load existing indices
- `build()` - Create new indices from data
- `search(query)` - Execute hybrid search
- `sync_indices()` - Update indices with new documents

### 2. Retrieval Engine

#### A. Hybrid Search (brain_service.py, retrieve.py)

Combines two retrieval methods:

**Vector Search (Semantic)**
- Tool: FAISS index
- Method: Embedding similarity
- Speed: Fast (< 100ms)
- Strength: Understands meaning

**Keyword Search (Lexical)**
- Tool: BM25 index
- Method: Term frequency matching
- Speed: Very fast (< 10ms)
- Strength: Matches exact terminology

**Fusion Strategy:** Reciprocal Rank Fusion (RRF)
- More robust than simple weighted average
- Configurable via `hybrid_search_config.py`
- Pre-tuned profiles for different domains

#### B. Reranking

**File:** `src/core/reranker.py`

Cross-encoder model for final refinement:
- Takes top-k results
- Re-scores based on query relevance
- Returns re-ranked list
- Optional (can disable for speed)

### 3. Generation Engine

**File:** `src/core/generate.py`

Responsible for LLM interaction:

**Prompt Management:**
- Build context-aware prompts
- Include conversation history
- Format retrieved documents
- Add special instructions

**Answer Generation:**
- Call Ollama local LLM
- Stream responses for real-time UI
- Extract source citations

**Query Rewriting:**
- Improve ambiguous queries
- Add context from conversation
- Generate follow-up queries

### 4. Conversation Context

**File:** `src/core/conversation_context.py`

Multi-turn conversation awareness:

**Features:**
- Session history retrieval
- Entity/topic extraction
- Follow-up detection
- Query rewriting with context
- Conversation summarization

**Benefits:**
- Better follow-up question handling
- Maintains context across turns
- Enables natural dialogue

### 5. Faithfulness Checker

**File:** `src/core/faithfulness_check.py`

Quality assurance for generated answers:

**Scoring Components:**
- Token overlap (25%) - Surface-level matching
- Semantic consistency (30%) - Meaning alignment
- Entity grounding (25%) - Fact verification
- Contradiction detection (20%) - Logic consistency

**Output:**
- Overall score (0.0-1.0)
- Component breakdown
- Specific concerns list
- Confidence level

### 6. Data Processing Pipeline

**Files:** `src/data/load_data.py`, `src/data/split_text.py`

Document handling:

**Load:**
- PDF, DOCX, XLSX, CSV, TXT
- Extracts metadata (source, page)
- Preserves document structure

**Split:**
- Recursive character splitting
- Configurable chunk size
- Overlap for context preservation
- Metadata attached to chunks

### 7. Storage Layer

**Files:** `src/storage/chat_store.py`

Persistent storage:

**Chat History:**
- SQLite database
- Session-based organization
- Message history per session
- Metadata (timestamps, user)

**Indices:**
- FAISS vector store (memory + disk)
- BM25 index (pickle format)
- Index state metadata (JSON)

---

## Data Flow

### 1. Indexing Pipeline

```
Raw Documents
    ↓
load_data.py (Multiple formats)
    ↓
Document objects (with metadata)
    ↓
split_text.py (Chunking)
    ↓
Text chunks with metadata
    ↓
┌─────────────────────────────────┐
│ embed_store.py                  │
├─────────────────────────────────┤
│ Generate embeddings (BGE-M3)    │
│ Build FAISS index               │
│ Build BM25 index                │
│ Save to disk                    │
└─────────────────────────────────┘
    ↓
Indices ready for search
```

### 2. Query Pipeline

```
User Input
    ↓
conversation_context.py
├─ Load session history
├─ Extract entities/topics
├─ Detect follow-up vs new
└─ Enhance with context
    ↓
Enhanced Query
    ↓
brain_service.py (orchestrator)
    ↓
retrieve.py (hybrid search)
├─ Vector search (FAISS)
│  ├─ Embed query
│  ├─ Similarity search
│  └─ Get scores
│
└─ Keyword search (BM25)
   ├─ Tokenize query
   ├─ BM25 ranking
   └─ Get scores
    ↓
hybrid_search_config.py
├─ Apply RRF fusion
├─ Normalize scores
└─ Combine results
    ↓
reranker.py (optional)
├─ Cross-encoder reranking
└─ Final ranking
    ↓
Ranked Documents
```

### 3. Generation Pipeline

```
Ranked Documents + Query
    ↓
generate.py
├─ Extract sources
├─ Format documents
├─ Build prompt
└─ Include context summary
    ↓
Ollama LLM
├─ Generate answer
└─ Stream response
    ↓
Generated Answer
    ↓
faithfulness_check.py (optional)
├─ Token overlap check
├─ Semantic consistency check
├─ Entity grounding check
├─ Contradiction detection
└─ Score & flag concerns
    ↓
Answer + Confidence + Sources
    ↓
UI Display
    ↓
User Response
```

---

## Configuration Management

**File:** `src/core/config_service.py`

Centralized configuration:

```python
config = ConfigManager()

# Key settings:
config.data_folder      # Input document directory
config.index_folder     # Output indices location
config.model_folder     # LLM model directory
config.embedding_model  # Which embedding model
config.llm_model        # Which LLM to use
config.chunk_size       # Text splitting size
config.chunk_overlap    # Chunk overlap for context
```

---

## Logging & Monitoring

**File:** `src/core/logging_config.py`

Comprehensive logging throughout system:

```
INFO level: Feature usage (search queries, generation)
DEBUG level: Detailed timings and component states
ERROR level: Failures and degradations
```

---

## Performance Characteristics

### Latency Breakdown (per query)

| Component | Time | Notes |
|-----------|------|-------|
| Context extraction | < 5ms | Database lookup |
| Vector search | 50-150ms | FAISS embedding + search |
| BM25 search | 5-30ms | Tokenization + ranking |
| RRF fusion | < 1ms | Rank combination |
| Reranking | 100-500ms | Optional, cross-encoder |
| LLM generation | 2-10s | Streaming from local model |
| Faithfulness check | 100-500ms | Optional, offline only |
| **Total (w/o LLM)** | **200-800ms** | Database to ranked docs |
| **Total (with LLM)** | **3-12s** | Full pipeline |

### Memory Usage

| Component | Size | Location |
|-----------|------|----------|
| FAISS index | 300-500 MB | RAM |
| BM25 index | 50-100 MB | RAM |
| Models | 3-5 GB | Disk + RAM (loaded) |
| Chat history | < 10 MB | SQLite on disk |
| Session cache | 10-50 MB | RAM |

---

## Scalability Considerations

### Horizontal Scaling

Multiple instances of UI can share:
- Single FAISS index (read-only via network)
- Single BM25 index (read-only)
- Single Ollama LLM server (via API)

### Vertical Scaling

For larger datasets:
- Shard FAISS index by topic
- Use GPU acceleration for embeddings
- Increase Ollama context window
- Add caching layer

### Optimization Points

1. **Search Speed:**
   - Use smaller embedding models
   - Reduce rerank_top_k
   - Disable cross-encoder reranking

2. **Memory:**
   - Stream embeddings instead of loading full index
   - Use CPU-only FAISS
   - Implement index sharding

3. **Generation Speed:**
   - Use smaller LLM
   - Reduce prompt context window
   - Increase Ollama batch size

---

## Extension Points

### Adding New Components

1. **New Retriever Type:**
   - Implement in `retrieve.py`
   - Integrate into `hybrid_search_config.py`
   - Add to `brain_service.search()`

2. **New Validation Check:**
   - Implement scoring function
   - Add to `faithfulness_check.py`
   - Integrate into generation pipeline

3. **New Data Source:**
   - Add loader to `data/load_data.py`
   - Register in `DirectoryLoader`
   - Document supported formats

4. **New UI:**
   - Create in `src/ui/`
   - Import `brain_service` and `chat_store`
   - Follow chat interface pattern

---

## Error Handling Strategy

All major components include graceful degradation:

```python
# Example: Reranking fails
try:
    reranked = reranker.rank(top_docs)
except Exception as e:
    log_error(f"Reranking failed: {e}")
    reranked = top_docs  # Use unranked results
```

Benefits:
- System never crashes
- Partial results better than nothing
- Errors logged for debugging
- Monitoring tracks failures

