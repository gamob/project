# Corporate Brain v1.0

A local, air-gapped Retrieval-Augmented Generation (RAG) system built with Streamlit, LangChain, FAISS, BM25, and Ollama.

> **Status:** ✅ Production-ready with three powerful new RAG features

---

## Overview

Corporate Brain is designed for **secure, offline document intelligence** without sending data to external services. It's tested on high-performance servers (96 cores CPU, dual A2 GPU) and balances semantic search with keyword retrieval for enterprise-grade question answering.

### Core Capabilities

- 🔍 **Hybrid Search** - Semantic embeddings + BM25 keyword matching with RRF fusion
- 🎯 **Smart Ranking** - Reciprocal Rank Fusion for robust result ranking
- 🔄 **Multi-turn Conversations** - Session-aware context for better follow-ups
- ✅ **Quality Assurance** - Faithfulness checking to detect hallucinations
- 💾 **Persistent Chat** - SQLite-based conversation history
- 🌐 **Web & Terminal UI** - Both Streamlit web and CLI interfaces
- 📄 **Multi-format Documents** - PDF, DOCX, XLSX, CSV, TXT support
- 🚀 **Streaming Responses** - Real-time answer generation

---

## Quick Start

### Prerequisites

- Python 3.8+
- 8+ GB RAM (16 GB recommended)
- Ollama installed and running
- Documents in `data/` folder

### Installation

```bash
# Clone repository
cd project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
# Web UI (Streamlit)
streamlit run src/ui/app.py

# Terminal UI
python src/ui/app_terminal.py
```

Then:
1. Upload documents in the sidebar
2. Click "Sync Brain" to build indices
3. Ask questions in the chat interface

---

## New Features (May 2026)

Three powerful features were recently added:

### 1. Chat History Memory for RAG ✨
Smart context extraction for multi-turn conversations. Automatically detects follow-ups and rewrites queries with context.

**File:** `src/core/conversation_context.py`

```python
from conversation_context import integrate_conversation_context

context = integrate_conversation_context("Tell me more", session_id=123)
enhanced_query = context["enhanced_query"]  # Better search query
```

### 2. Refined Hybrid Search with RRF 🎯
Replaces simple weighted average with industry-standard Reciprocal Rank Fusion for more stable, robust results.

**File:** `src/core/hybrid_search_config.py`

```python
from hybrid_search_config import get_semantic_config

config = get_semantic_config()  # Pre-tuned: 70% vector, 30% BM25
```

### 3. Faithfulness Checking ✅
Automatically detects hallucinations and validates answer grounding in source documents.

**File:** `src/core/faithfulness_check.py`

```python
from faithfulness_check import evaluate_answer_faithfulness

score = evaluate_answer_faithfulness(answer, documents)
if score['is_faithful']:
    print("✓ Answer is grounded in documents")
```

**Learn more:** See [NEW_FEATURES_SUMMARY.md](docs/NEW_FEATURES_SUMMARY.md)

---

## Documentation

Complete documentation organized by use case:

### 📚 For Everyone
- **[README.md](README.md)** — This file, project overview
- **[QUICK_START.md](docs/QUICK_START.md)** — Getting started guide
- **[DEPENDENCIES.md](docs/DEPENDENCIES.md)** — Library requirements

### 🎯 For Feature Users
- **[FEATURES_AT_A_GLANCE.md](docs/FEATURES_AT_A_GLANCE.md)** — Visual overview of new features
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** — One-page developer cheat sheet
- **[INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md)** — Complete integration examples

### 🏗️ For Developers
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design and data flow
- **[AI_CONTEXT.md](docs/AI_CONTEXT.md)** — Codebase overview for AI agents
- **[IMPLEMENTATION_COMPLETE.md](docs/IMPLEMENTATION_COMPLETE.md)** — Feature implementation details

### 🔧 Additional Guides
- **[TERMINAL_README.md](docs/TERMINAL_README.md)** — Terminal UI guide
- **[TERMINAL_CONFIG_GUIDE.md](docs/TERMINAL_CONFIG_GUIDE.md)** — Terminal configuration
- **[MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)** — Upgrade and migration information

---

## Project Structure

```
corporate-brain/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
│
├── data/                        # Input documents (user-provided)
├── faiss_index/                 # Vector search index
│
├── model/                       # Local models
│   ├── Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf
│   ├── bge-m3/                  # Embedding model
│   └── bge-reranker-v2-m3/      # Reranking model
│
├── docs/                        # Documentation (you are here!)
│   ├── QUICK_START.md
│   ├── ARCHITECTURE.md
│   ├── INTEGRATION_GUIDE.md
│   ├── FEATURES_AT_A_GLANCE.md
│   └── ...
│
├── evaluation/                  # Evaluation datasets
│
└── src/                         # Main application code
    ├── app.py                   # Streamlit entry point
    ├── app_terminal.py          # Terminal UI entry point
    │
    ├── core/                    # RAG engine
    │   ├── brain_service.py     # Orchestrator
    │   ├── retrieve.py          # Search engine
    │   ├── hybrid_search_config.py
    │   ├── conversation_context.py
    │   ├── generate.py          # LLM interaction
    │   ├── faithfulness_check.py
    │   └── ...
    │
    ├── data/                    # Document processing
    │   ├── load_data.py
    │   └── split_text.py
    │
    ├── ui/                      # User interfaces
    │   ├── app.py              # Streamlit web UI
    │   └── app_terminal.py     # Terminal UI
    │
    ├── storage/                 # Data persistence
    │   └── chat_store.py       # Chat history
    │
    └── eval/                    # Evaluation tools
        └── generate_evals.py
```

---

## Key Components

### Brain Service (src/core/brain_service.py)
Central orchestrator managing index lifecycle and search operations.

### Retrieval Engine (src/core/retrieve.py)
Hybrid retrieval combining:
- **Vector search** (FAISS) - Semantic similarity
- **Keyword search** (BM25) - Exact term matching
- **RRF fusion** - Rank-based result combination

### Generation Engine (src/core/generate.py)
- Prompt construction and context inclusion
- Streaming LLM responses via Ollama
- Source citation extraction

### Conversation Context (src/core/conversation_context.py)
- Session history management
- Follow-up question detection
- Context-aware query rewriting

### Faithfulness Checker (src/core/faithfulness_check.py)
- Token overlap analysis
- Semantic consistency scoring
- Entity grounding verification
- Contradiction detection

---

## Performance

Typical latency on 96-core CPU server with dual A2:

| Operation | Time | Notes |
|-----------|------|-------|
| Vector Search | 50-150ms | FAISS embedding + search |
| BM25 Search | 5-30ms | Tokenization + ranking |
| Search + Fusion | 100-200ms | Hybrid retrieval |
| Reranking (optional) | 100-500ms | Cross-encoder |
| LLM Generation | 2-10s | Streaming output |
| **Full Pipeline** | **3-12s** | Including LLM generation |

Memory usage:
- **FAISS Index:** 300-500 MB
- **BM25 Index:** 50-100 MB
- **Models:** 3-5 GB (loaded)
- **Session Cache:** 10-50 MB

---

## Why This Project

This repository addresses the need for **secure, offline document intelligence**:

- ✅ **Private** - No data sent to external services
- ✅ **Fast** - Local models with GPU acceleration available
- ✅ **Reliable** - Deterministic results, no API dependencies
- ✅ **Flexible** - Multi-format document support
- ✅ **Conversational** - Multi-turn chat with context awareness
- ✅ **Trustworthy** - Faithfulness checking to prevent hallucinations

**Ideal for:**
- Enterprise document Q&A systems
- Sensitive data analysis
- Offline environments
- Teams requiring data privacy
- Vietnamese/English language support

---

## Configuration

Edit `src/config.json` to customize:

```json
{
  "data_folder": "data",
  "index_folder": "faiss_index",
  "model_folder": "model",
  "embedding_model": "bge-m3",
  "llm_model": "llama2",
  "chunk_size": 1000,
  "chunk_overlap": 100
}
```

---

## Troubleshooting

### Ollama Connection Error
```bash
ollama serve  # Start Ollama in another terminal
```

### FAISS Index Issues
```bash
# Rebuild indices
python -c "from src.core.brain_service import Brain; b=Brain(); b.build()"
```

### Memory Issues
- Reduce `chunk_size` in config
- Use smaller embedding model
- Disable cross-encoder reranking

See [docs/QUICK_START.md](docs/QUICK_START.md) for more troubleshooting.

---

## Support

- 📖 Full documentation in `docs/` folder
- 🐛 Check logs for detailed error messages
- 🔧 See [INTEGRATION_GUIDE.md](docs/INTEGRATION_GUIDE.md) for integration examples

---

## Project Structure

- `data/` — source documents
- `src/` — source code and app logic
- `src/core/` — retrieval, indexing, generation, and brain orchestration
- `src/ui/` — UI interfaces
- `src/storage/` — chat session persistence
- `src/docs/` — developer notes and upgrade logs

## License

MIT License

Copyright (c) 2026 quang minh

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
