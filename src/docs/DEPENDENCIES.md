# Project Dependencies

Complete list of Python dependencies required for the Corporate Brain RAG system.

**Primary Manager:** `requirements.txt`

---

## Installation

```bash
pip install -r requirements.txt
```

Or install specific groups:

```bash
# Core UI and utilities
pip install streamlit rich

# RAG & LLM framework
pip install langchain langchain-community langchain-ollama langchain-huggingface

# Vector search and indexing
pip install faiss-cpu bm25s

# Embeddings
pip install sentence-transformers huggingface-hub

# Data processing
pip install PyPDF2 python-docx openpyxl pandas

# Utilities
pip install requests python-dotenv ollama
```

---

## Dependency Groups

### Core UI & Display

| Package | Version | Purpose |
|---------|---------|---------|
| **streamlit** | 1.28.1 | Web UI framework for data apps |
| **rich** | 13.7.0 | Beautiful terminal formatting and progress bars |

### RAG & LLM Framework

| Package | Version | Purpose |
|---------|---------|---------|
| **langchain** | 0.1.9 | Orchestration framework for LLM applications |
| **langchain-community** | 0.0.20 | Community integrations for LangChain |
| **langchain-ollama** | 0.1.0 | Ollama LLM integration for local models |
| **langchain-huggingface** | 0.0.30 | HuggingFace integrations (embeddings, models) |

### Vector Search & Indexing

| Package | Version | Purpose |
|---------|---------|---------|
| **faiss-cpu** | 1.7.4 | Fast similarity search for embeddings |
| **bm25s** | 0.2.1 | BM25 keyword search indexing |

### Embeddings & Models

| Package | Version | Purpose |
|---------|---------|---------|
| **sentence-transformers** | 2.2.2 | Pre-trained embedding models (semantic search) |
| **huggingface-hub** | 0.19.4 | Download models from HuggingFace Hub |

### Data Processing

| Package | Version | Purpose |
|---------|---------|---------|
| **PyPDF2** | 3.0.1 | PDF document parsing |
| **python-docx** | 0.8.11 | Microsoft Word document parsing |
| **openpyxl** | 3.1.2 | Excel spreadsheet handling |
| **pandas** | 2.1.3 | Data manipulation and analysis |

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| **requests** | 2.31.0 | HTTP client for API calls |
| **python-dotenv** | 1.0.0 | Load environment variables from .env |
| **ollama** | 0.1.9 | Ollama local LLM runtime client |
| **sqlite3** | 2.6.0 | Embedded database for chat history |

---

## Feature-Specific Dependencies

### Chat History (conversation_context.py)

```
- langchain (Document handling)
- sqlite3 (Session storage)
- pandas (Data manipulation)
```

### Hybrid Search (hybrid_search_config.py)

```
- faiss-cpu (Vector search)
- bm25s (Keyword search)
- sentence-transformers (Embeddings)
```

### Faithfulness Checking (faithfulness_check.py)

```
- sentence-transformers (Semantic similarity)
- langchain (Document processing)
```

### Document Loading (data/load_data.py)

```
- PyPDF2 (PDF files)
- python-docx (Word documents)
- openpyxl (Excel spreadsheets)
- pandas (CSV/tabular data)
```

---

## Local Model Requirements

The system uses Ollama for local LLM inference. Required files:

### Ollama Installation

1. Install Ollama from https://ollama.ai
2. Download a model:
   ```bash
   ollama pull llama2  # or other model
   ```

### Model Files in Project

Located in `model/` directory:

| File | Purpose |
|------|---------|
| `Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf` | Quantized Llama model for generation |
| `bge-m3/` | BGE-M3 embedding model for semantic search |
| `bge-reranker-v2-m3/` | Cross-encoder for reranking results |

---

## Memory & Hardware Requirements

### Recommended

- **RAM:** 16 GB (minimum 8 GB)
- **GPU:** Optional (CUDA for faster embeddings)
- **Storage:** 20-30 GB for models

### Index Files

| File | Size | Purpose |
|------|------|---------|
| `faiss_index/index.faiss` | ~500 MB | Vector search index |
| `index_state.json` | ~1 MB | Index metadata |
| Model files | ~10 GB | Embeddings and LLMs |

---

## Python Version

- **Minimum:** Python 3.8
- **Recommended:** Python 3.10+

---

## Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Troubleshooting

### ImportError for specific packages

```bash
# Reinstall specific package
pip install --upgrade package_name

# Or reinstall all
pip install --upgrade -r requirements.txt
```

### FAISS issues (especially on Windows)

```bash
# Try CPU version (already default)
pip install faiss-cpu

# Or GPU version if you have CUDA
pip install faiss-gpu
```

### HuggingFace model download issues

```bash
# Set cache directory
export HF_HOME=/path/to/cache
pip install -U huggingface-hub
```

### Ollama connection issues

```bash
# Verify Ollama is running
ollama serve  # Start Ollama (in another terminal)

# Check connection
python -c "from langchain_ollama import OllamaLLM; m=OllamaLLM(model='llama2'); print(m)"
```

---

## Optional Dependencies

For development and testing:

```bash
pip install pytest pytest-cov black flake8 mypy
```

---

## Version Compatibility

All versions specified in `requirements.txt` are tested and compatible. To upgrade:

```bash
# Check for outdated packages
pip list --outdated

# Carefully upgrade
pip install --upgrade package_name
```

For a safe upgrade of all packages:

```bash
pip install --upgrade -r requirements.txt --dry-run  # Preview changes
pip install --upgrade -r requirements.txt  # Apply changes
```

