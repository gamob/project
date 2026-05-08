# Terminal App Configuration Guide

## Overview

The `app_terminal.py` works with your existing configuration files and services. This guide explains how to optimize it for your specific setup.

## Core Configuration Files

### 1. `src/config.json` (Existing)
Controls LLM and embedding models:

```json
{
  "llm_model": "llama2:13b",
  "embedding_model": "bge-m3",
  "temperature": 0.7,
  "top_k": 10,
  "max_tokens": 512
}
```

**For Terminal App (Recommended GPU Settings):**

```json
{
  "llm_model": "llama2:70b",
  "embedding_model": "bge-m3",
  "temperature": 0.7,
  "top_k": 15,
  "max_tokens": 1024,
  "num_threads": 0,
  "num_gpu": -1
}
```

### 2. Brain Service Configuration
Modify in `src/brain_service.py`:

```python
# Find this section and adjust:
class Brain:
    def __init__(self):
        self.embedding_model = "bge-m3"  # Or smaller: "bge-small"
        self.search_top_k = 15  # Increase for better results
        self.batch_size = 32  # Increase for faster processing
```

## Optimization by Use Case

### Use Case 1: Large Model on GPU (Recommended)

**Goal:** Run 13B-70B model on dedicated GPU server

**Config:**
```json
{
  "llm_model": "llama2:70b",
  "embedding_model": "bge-m3",
  "temperature": 0.7,
  "top_k": 15,
  "max_tokens": 1024,
  "batch_size": 64
}
```

**Ollama Setup:**
```bash
# Pull large model
ollama pull llama2:70b

# Set GPU layers (VRAM specific)
# Adjust NUM_GPU based on your VRAM:
# 24GB VRAM: NUM_GPU=40
# 40GB VRAM: NUM_GPU=80
# Full GPU: NUM_GPU=-1

export OLLAMA_GPU=true
ollama serve
```

**Terminal Command:**
```bash
cd src
python app_terminal.py
```

**Expected Performance:**
- First query: 30-60 seconds (model load)
- Subsequent queries: 5-15 seconds
- Memory: 50-100MB Python + 20GB+ GPU VRAM

### Use Case 2: Smaller Model on Shared GPU

**Goal:** Run smaller, faster model to share GPU

**Config:**
```json
{
  "llm_model": "mistral:7b",
  "embedding_model": "bge-small-en-v1.5",
  "temperature": 0.7,
  "top_k": 10,
  "max_tokens": 512,
  "batch_size": 16
}
```

**Setup:**
```bash
ollama pull mistral:7b
ollama pull bge-small-en-v1.5
ollama serve
```

**Performance:**
- First query: 10-20 seconds
- Subsequent: 2-5 seconds
- Memory: ~8-12GB VRAM

### Use Case 3: CPU-Only (Fallback)

**Goal:** Run on CPU if no GPU available

**Config:**
```json
{
  "llm_model": "neural-chat:7b",
  "embedding_model": "bge-small-en-v1.5",
  "temperature": 0.5,
  "top_k": 5,
  "max_tokens": 256,
  "num_threads": 8
}
```

**Setup:**
```bash
export OLLAMA_NUM_THREAD=8
ollama pull neural-chat:7b
ollama serve
```

**Performance:**
- Query time: 30-120 seconds (depends on CPU)
- Memory: 200-400MB Python + 4-8GB RAM

## Environment Variables

Create `src/.env` file:

```bash
# Ollama configuration
OLLAMA_HOST=localhost:11434
OLLAMA_MODEL=llama2:70b
OLLAMA_NUM_THREAD=0
OLLAMA_NUM_GPU=-1

# App configuration
EMBEDDING_MODEL=bge-m3
VECTOR_DB_PATH=../faiss_index
DATA_PATH=../data

# Performance tuning
BATCH_SIZE=32
MAX_WORKERS=4
SEARCH_TOP_K=15

# Debug (optional)
DEBUG=false
LOG_LEVEL=INFO
```

**Load in app_terminal.py:**
```python
from dotenv import load_dotenv
load_dotenv()

model_name = os.getenv("OLLAMA_MODEL", "llama2:13b")
```

## Performance Tuning

### Memory Optimization

**Reduce Python memory footprint:**
```bash
# Use PyPy instead of CPython (if compatible)
pypy3 app_terminal.py

# Or use memory profiler to find leaks
pip install memory-profiler
python -m memory_profiler app_terminal.py
```

**Reduce model memory:**
```python
# In brain_service.py
max_workers = 1  # Reduce parallel processing
chunk_size = 256  # Smaller chunks
```

### GPU Memory Management

**For 24GB GPU:**
```bash
export OLLAMA_GPU_MEMORY=24000  # MB
export OLLAMA_NUM_LAYERS=35     # Load to GPU
ollama serve
```

**For 40GB GPU:**
```bash
export OLLAMA_GPU_MEMORY=40000
export OLLAMA_NUM_LAYERS=80     # Load entire model
ollama serve
```

**Monitor GPU usage:**
```bash
# On nvidia GPU:
nvidia-smi -l 1  # Update every 1 second

# For monitoring remotely:
watch -n 1 nvidia-smi
```

### Search Performance

**Tune search parameters:**
```python
# In app_terminal.py, modify _process_question():

# Increase search results
docs, _, conf = self.brain.search(query, extra_queries, k=20)

# Use only FAISS (faster but less accurate)
docs = self.brain.faiss_search(query)

# Use only BM25 (slower but keyword-aware)
docs = self.brain.bm25_search(query)
```

## Remote GPU Server Setup

### Initial Setup (One-time)

```bash
# SSH into server
ssh user@gpu-server

# Install dependencies
pip install -r requirements.txt

# Verify GPU
nvidia-smi

# Verify Ollama
ollama list

# Test model
ollama run llama2:70b "Hello"
```

### Daily Usage

**Option 1: Direct Connection (Simplest)**
```bash
ssh user@gpu-server
cd ~/project/src
python app_terminal.py
```

**Option 2: Using tmux (Persistent)**
```bash
# Start in tmux
ssh user@gpu-server
tmux new-session -s brain
cd ~/project/src
python app_terminal.py

# Detach: Ctrl+B, D

# Later, reattach:
ssh user@gpu-server
tmux attach -t brain
```

**Option 3: Using screen (Alternative)**
```bash
ssh user@gpu-server
screen -S brain
cd ~/project/src
python app_terminal.py

# Detach: Ctrl+A, D

# Later:
ssh user@gpu-server
screen -r brain
```

**Option 4: Systemd Service (Production)**
```bash
# Create /etc/systemd/system/brain.service
[Unit]
Description=Corporate Brain Terminal App
After=network.target

[Service]
Type=simple
User=brain
WorkingDirectory=/home/brain/project
ExecStart=/usr/bin/python3 src/app_terminal.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable brain
sudo systemctl start brain
sudo systemctl status brain
sudo journalctl -u brain -f  # View logs
```

## Model Recommendations

### By Use Case

| Use Case | Model | Embedding | GPU VRAM | Speed |
|----------|-------|-----------|----------|-------|
| **Quality** | llama2:70b | bge-m3 | 40GB+ | Slow |
| **Balance** | llama2:13b | bge-m3 | 24GB+ | Normal |
| **Fast** | mistral:7b | bge-small | 16GB+ | Fast |
| **Budget** | neural-chat:7b | bge-small | 12GB+ | Slow |
| **CPU-Only** | mistral:7b-q4 | bge-small | N/A | Very Slow |

### Download Model

```bash
# Get available models
ollama list

# Pull a model
ollama pull llama2:70b
ollama pull mistral:7b
ollama pull neural-chat:7b

# Remove unused models
ollama rm llama2:13b
```

## Monitoring & Debugging

### Check Resources

```bash
# System stats
free -h              # RAM
df -h                # Disk
nvidia-smi          # GPU (if NVIDIA)

# Process monitoring
ps aux | grep python
top -p $(pgrep -f app_terminal)
```

### Enable Debug Logging

Edit `app_terminal.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In methods:
logger.debug("Processing query: " + prompt)
logger.info("Brain search took 2.5s")
```

### Benchmark Model

```bash
# Test response time
time ollama run llama2:70b "Explain machine learning in 100 words"

# Test in app
python app_terminal.py
# Then ask: "What is machine learning?"
# Check time in terminal output
```

## Troubleshooting

### "Out of memory" Error

```bash
# Reduce model size
ollama pull mistral:7b  # Smaller than llama2:13b

# Or: Reduce batch size in config.json
# Or: Reduce search results (top_k)
```

### Slow First Query

**Normal!** First query loads model into GPU.
- Expected: 30-120 seconds
- Subsequent queries: 2-15 seconds
- Solution: Just wait, or keep app running

### Terminal Lag

```bash
# Check system load
load=$(uptime | awk -F'load average:' '{print $2}')

# If load > CPU count, system is overloaded
nproc  # Show CPU count
```

### GPU Not Used

```bash
# Verify GPU in Ollama
ollama list

# Check NVIDIA
nvidia-smi

# Force GPU in config
export OLLAMA_NUM_GPU=-1
ollama serve

# Test:
nvidia-smi  # Should show GPU memory usage
```

## Best Practices

1. ✅ Use tmux/screen for remote sessions
2. ✅ Monitor GPU with nvidia-smi
3. ✅ Keep Ollama running (don't restart frequently)
4. ✅ Tune top_k based on document size
5. ✅ Use smaller models for faster iteration
6. ✅ Back up faiss_index/ regularly
7. ✅ Test with small document set first

---

**Need help? Check logs or use the terminal app's built-in error messages.**
