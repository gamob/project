# Project Architecture and Codebase Overview

## Purpose

This document summarizes the important `src` modules and folders so developers can quickly identify which files to modify for requested changes.

**Note:** This repository is executed on a Linux GPU server, not on the current VS Code workstation.

---

## Top-Level `src` Files

- **app.py** - Minimal entrypoint that imports the Streamlit UI from `src/ui/app.py`.
- **app_terminal.py** - Terminal-based UI entry point. Similar to `src/ui/app.py` but for CLI interaction.
- **main_ui.py** - Secondary UI wrapper or higher-level UI entry script.
- **generate_evals.py**, **merge_eval_datasets.py**, **polish_eval_runner.py**, **prep_questions.py** - Evaluation/data preparation scripts used outside the main production flow.
- **config.json** - Runtime configuration file for project paths and settings.
- **__init__.py** - Marks `src` as a Python package.

---

## Key Folders

| Folder | Purpose | Contents |
|--------|---------|----------|
| `core/` | Primary logic for the Hybrid RAG system | Brain, retrieval, generation engines |
| `data/` | Document loading and chunking utilities | File loaders, text splitters |
| `docs/` | Developer notes, guides, and change logs | Integration guides, quick references |
| `eval/` | Evaluation workflows and dataset tooling | Evaluation runners, metrics |
| `storage/` | Persistence layer for chat sessions | Database helpers, message storage |
| `ui/` | Streamlit UI components and app structure | Web interface code |

---

## src/core Overview

Core RAG system logic. Most modifications happen here.

### Key Modules

| Module | Responsibility | Key Functions |
|--------|-----------------|----------------|
| **brain_service.py** | Central orchestrator for index lifecycle, incremental sync, and high-level search | `load()`, `build()`, `search()`, `sync_indices()` |
| **retrieve.py** | Hybrid retrieval engine. Manages vector + BM25 search, deduplication, score fusion, and reranking | `get_hybrid_docs()`, `fuse_hybrid_scores()`, `deduplicate_documents()` |
| **retrieval_service.py** | Singleton retrieval service wrapper around `retrieve.py`, eager-loading models and exposing a stable API | `initialize_retrieval_service()`, `get_retrieval_service()` |
| **hybrid_search_config.py** | Hybrid search policy and fusion settings. Defines normalization, RRF, and confidence behavior | `get_semantic_config()`, `get_keyword_config()`, `HybridSearchConfig` |
| **generate.py** | LLM prompt builder, search query rewriting, source extraction, and answer generation | `answer_question()`, `extract_sources()`, `build_prompt()` |
| **conversation_context.py** | Multi-turn session helper. Builds follow-up-aware search queries and short summaries from chat history | `integrate_conversation_context()`, `ConversationContext` |
| **embed_store.py** | Embedding and index helpers. Builds/saves FAISS vector stores, creates BM25 indices, and supports incremental updates | `create_vector_store()`, `build_bm25_index()`, `save_index()` |
| **index_service.py** | Index abstraction layer. Creates, loads, and updates vector + BM25 indices via `embed_store` | `load_indices()`, `update_indices()` |
| **reranker.py** | Cross-encoder reranker interface and implementation | `rerank_documents()` |
| **config_service.py** | Configuration loader and runtime settings provider | `ConfigManager`, `load_config()` |
| **faithfulness_check.py** | Quality check utilities for retrieval and answer faithfulness | `evaluate_answer_faithfulness()`, `FaithfulnessChecker` |
| **main.py** | Secondary brain or application entrypoint for scripts | Initialization examples |
| **logging_config.py** | Logging setup and formatting utilities | `setup_logging()` |
| **__init__.py** | Package marker | — |

### Data Flow Diagram

```
User Query
    ↓
conversation_context.py (enhance with history)
    ↓
brain_service.py (orchestrate)
    ↓
retrieve.py + hybrid_search_config.py (search)
    ├─ Vector search (FAISS)
    └─ Keyword search (BM25)
    ↓
reranker.py (cross-encoder reranking)
    ↓
generate.py (LLM generation)
    ↓
faithfulness_check.py (validation)
    ↓
User Response
```

---

## src/data Overview

Document loading and text splitting utilities.

### Modules

| Module | Purpose |
|--------|---------|
| **load_data.py** | Loads documents from `data/` folder in multiple formats (PDF, TXT, DOCX, etc) |
| **split_text.py** | Splits documents into chunks for embedding |

### Common Usage

```python
from load_data import load_documents
from split_text import split_docs

docs = load_documents("path/to/data")
chunks = split_docs(docs, chunk_size=1000, overlap=100)
```

---

## src/ui Overview

Streamlit-based web interface for the RAG system.

### Modules

| Module | Purpose |
|--------|---------|
| **app.py** | Main Streamlit frontend users interact with. Handles UI, user input, streaming response display, and session state |
| **app_terminal.py** | CLI-based interface for terminal sessions |
| **main_ui.py** | Possibly a wrapper around the primary UI flow |

### Running the UI

```bash
streamlit run src/ui/app.py
```

---

## src/storage Overview

Persistence layer for chat sessions and metadata.

### Modules

| Module | Purpose |
|--------|---------|
| **chat_store.py** | SQLite persistence for chat sessions, messages, and conversation history |

### Common Usage

```python
from chat_store import (
    init_db, create_session, save_message,
    load_session_messages, get_all_sessions
)

init_db()
session_id = create_session("New Chat")
save_message(session_id, "user", "Hello!")
messages = load_session_messages(session_id)
```

---

## src/eval Overview

Evaluation workflows for QA system validation.

### Modules

| Module | Purpose |
|--------|---------|
| **generate_evals.py** | Generates evaluation datasets and runs QA evaluation |
| **merge_eval_datasets.py** | Merges multiple evaluation dataset files |
| **polish_eval_runner.py** | Quality improvement runner for evaluation results |
| **prep_questions.py** | Prepares and formats questions for evaluation |

---

## Common Modification Scenarios

### "I need to improve search results"

Modify:
1. `src/core/retrieve.py` - Adjust fusion weights or reranking
2. `src/core/hybrid_search_config.py` - Change search profiles
3. `src/core/brain_service.py` - Update search logic

### "I need to improve answer quality"

Modify:
1. `src/core/generate.py` - Update prompt templates or LLM settings
2. `src/core/faithfulness_check.py` - Adjust hallucination detection
3. `src/core/retrieve.py` - Get better documents

### "I need to add a new feature"

1. Understand what feature does (search? generate? validate?)
2. Add to appropriate module in `src/core/`
3. Integrate into `src/ui/app.py`
4. Test with `src/eval/generate_evals.py`

### "I need to change the UI"

Modify:
1. `src/ui/app.py` - Streamlit interface
2. `src/ui/app_terminal.py` - Terminal interface

### "I need to add document types"

Modify:
1. `src/data/load_data.py` - Add document loader
2. `src/data/split_text.py` - Update splitting if needed

---

## Configuration Files

| File | Purpose |
|------|---------|
| `src/config.json` | Runtime paths and settings |
| `requirements.txt` | Python package dependencies |
| `src/.env` (optional) | Environment variables |

---

## Performance Considerations

- **Vector Search:** FAISS index in memory (fast but large)
- **Keyword Search:** BM25 loaded at startup (memory-efficient)
- **Reranking:** Cross-encoder (slow, optional)
- **Faithfulness:** Multi-component check (slow, offline only)
- **Chat History:** SQLite lookups (very fast)

---

## Development Workflow

1. **Load or Build Index**
   ```python
   from src.core.brain_service import Brain
   brain = Brain()
   brain.load()  # or brain.build()
   ```

2. **Search**
   ```python
   docs, conf, score = brain.search("Query")
   ```

3. **Generate**
   ```python
   from src.core.generate import answer_question
   answer, sources = answer_question("Query", docs)
   ```

4. **Validate**
   ```python
   from src.core.faithfulness_check import evaluate_answer_faithfulness
   faith = evaluate_answer_faithfulness(answer, docs)
   ```

---

## Testing

Run the evaluation suite:
```bash
cd src/eval
python generate_evals.py --dataset test --sample 10
```

Check individual components:
```bash
python src/core/main.py  # Interactive search loop
```

