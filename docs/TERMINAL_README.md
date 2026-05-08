# 🦖 Corporate Brain - Terminal Edition

A terminal-based UI version of the RAG (Retrieval-Augmented Generation) chatbot application using the **Rich** library for beautiful terminal formatting.

## Features

✨ **All functionality from the web version, now in your terminal:**

- 💬 **Interactive Chat** - Ask questions about your uploaded documents
- 📂 **Document Management** - Upload, delete, and manage documents
- 🔄 **Smart Brain Sync** - Index documents with FAISS + BM25
- ☢️ **Full Rebuild** - Reset and rebuild indices from scratch
- 📝 **Session Management** - Save, load, rename, and delete chat sessions
- 🎨 **Beautiful Terminal UI** - Rich panels, tables, progress indicators, and colors
- 📚 **Source Citations** - See exactly which documents provided your answers
- 📊 **Confidence Scores** - Understand retrieval confidence levels

## System Requirements

- Python 3.8+
- Ollama running locally (for LLM inference)
- GPU access (recommended for bigger models)

## Installation

### 1. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or install manually
pip install rich streamlit langchain langchain-community langchain-ollama langchain-huggingface faiss-cpu bm25s sentence-transformers
```

### 2. Ensure Ollama is Running

```bash
# Start Ollama (if not already running)
ollama serve
```

### 3. Verify Model

Make sure you have a model loaded in Ollama:
```bash
ollama list
```

If needed, pull the recommended model:
```bash
ollama pull llama2:13b
```

## Quick Start

### Option 1: Windows Batch Script (Easiest)
```bash
run_terminal.bat
```

### Option 2: Direct Python
```bash
cd src
python app_terminal.py
```

### Option 3: With Python Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd src
python app_terminal.py
```

## Usage Guide

### Main Menu Options

```
1. 💬 Chat
   - Enter chat mode and ask questions
   - Type 'exit' or 'quit' to return to menu
   - View conversation history
   - Auto-saves all conversations

2. 📂 Manage Documents
   - View uploaded documents with file sizes
   - Upload new documents (PDF, TXT, MD, DOCX, PPTX, XLSX, CSV)
   - Delete documents
   - Browse your document library

3. 🔄 Sync Brain
   - Reindex all documents
   - Updates FAISS vector index
   - Rebuilds BM25 search index
   - Use after uploading/deleting documents

4. ☢️  Nuke & Rebuild
   - Completely delete all indices
   - Rebuild from scratch
   - Warning: This takes time with large document sets

5. 📝 Chat Sessions
   - View all previous conversations
   - Load previous sessions
   - Rename sessions
   - Delete sessions

6. ❌ Exit
   - Close the application
```

### Chat Commands

While in chat mode:
- Type your question normally
- Type `exit` or `quit` to return to main menu
- Press Ctrl+C to force exit

### File Upload

You can upload documents in these formats:
- 📄 PDF (.pdf)
- 📝 Text (.txt)
- 📋 Markdown (.md)
- 📘 Word (.docx)
- 🎤 PowerPoint (.pptx)
- 📊 Excel (.xlsx)
- 📈 CSV (.csv)

**Note:** After uploading documents, always run "Sync Brain" to reindex them.

## Performance Tips for GPU Servers

### 1. Large Models

On a GPU server, you can use larger models:
```bash
ollama pull llama2:70b        # 70B model
ollama pull mistral:latest    # More efficient
ollama pull neural-chat       # Smaller, fast
```

### 2. Model Configuration

Adjust in `src/config.json`:
```json
{
  "llm_model": "llama2:70b",
  "embedding_model": "bge-m3",
  "search_top_k": 10
}
```

### 3. Terminal Recommendations

For best experience on remote GPU servers:
- Use **tmux** or **screen** to keep the app running over SSH
- Use **byobu** for a nicer terminal experience
- Run on a dedicated terminal multiplexer session

```bash
# Using tmux
tmux new-session -d -s brain
tmux send-keys -t brain "cd ~/project && python src/app_terminal.py" Enter
tmux attach -t brain
```

### 4. GPU Memory Management

For running on limited GPU memory:
- Reduce model context window
- Batch process documents during sync
- Use smaller embedding models

## Architecture

```
app_terminal.py
├── TerminalBrain (main class)
│   ├── _initialize_brain() - Setup Brain service
│   ├── show_main_menu() - Main menu interface
│   ├── chat_mode() - Interactive chat
│   ├── manage_documents() - Document CRUD
│   ├── manage_sessions() - Session management
│   └── _process_question() - RAG pipeline
├── Rich Components
│   ├── Console - Output rendering
│   ├── Panel - Bordered sections
│   ├── Table - Formatted data
│   ├── Progress - Loading indicators
│   └── Prompt - User input
└── Brain Service (imports)
    ├── Brain - RAG orchestration
    ├── generate - LLM responses
    └── chat_store - Session storage
```

## Comparison: Web vs Terminal

| Feature | Web (Streamlit) | Terminal (Rich) |
|---------|---|---|
| UI Type | Web Browser | Terminal TUI |
| Server Dependency | HTTP Server | None |
| Memory Footprint | Medium-High | Low |
| GPU-Friendly | Yes | Yes ✓ |
| Remote Access | Browser (Port needed) | SSH Direct ✓ |
| Beautiful UI | Yes | Yes ✓ |
| Setup Complexity | Medium | Low ✓ |
| Performance | Good | Excellent ✓ |

## Troubleshooting

### "Ollama not connected"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### "No documents loaded"
1. Upload documents via option 2
2. Run "Sync Brain" (option 3)
3. Wait for indexing to complete

### "Brain takes too long to sync"
- Normal for large document sets
- Consider splitting documents first
- Increase model context window in config.json

### Terminal not responding to input
- Press Enter explicitly after typing
- Check for stuck processes: `tasklist | grep python`
- Restart the application

### Permission errors on Linux/Mac
```bash
chmod +x src/app_terminal.py
python src/app_terminal.py
```

### "missing ScriptRunContext" warnings on Linux (Tons of repeated warnings)

**Problem:** On Linux servers, you see repeated warnings:
```
missing ScriptRunContext! This warning can be ignored when running in bare mode.
```

**Solution:** These are harmless Streamlit warnings inherited from dependencies. They're already suppressed in the code, but if they still appear:

**Option 1 - Use the Linux launcher script (Recommended):**
```bash
chmod +x run_terminal.sh
./run_terminal.sh
```

**Option 2 - Set environment variables before running:**
```bash
export STREAMLIT_LOGGER_LEVEL=error
export PYTHONWARNINGS="ignore::UserWarning"
python src/app_terminal.py
```

**Option 3 - Suppress in ~/.bashrc (Permanent):**
```bash
# Add to ~/.bashrc
export STREAMLIT_LOGGER_LEVEL=error
export PYTHONWARNINGS="ignore::UserWarning"

# Then:
source ~/.bashrc
python src/app_terminal.py
```

**Option 4 - Redirect stderr if warnings still appear:**
```bash
python src/app_terminal.py 2>&1 | grep -v "ScriptRunContext"
```

**Note:** These warnings don't affect functionality — they're just noise from Streamlit's initialization code.

## Advanced: Running on Remote GPU Server

### Setup (One-time)

```bash
ssh user@gpu-server

# Clone/setup project
cd ~/project
pip install -r requirements.txt

# Start Ollama in background
nohup ollama serve > ollama.log 2>&1 &
```

### Daily Usage

```bash
ssh user@gpu-server
cd ~/project

# Use tmux for persistent session
tmux new-session -s brain
python src/app_terminal.py
```

Then later:
```bash
tmux attach -t brain
```

## Environment Variables

Create a `.env` file in the project root:

```
OLLAMA_HOST=localhost:11434
OLLAMA_MODEL=llama2
EMBEDDING_MODEL=bge-m3
VECTOR_DB_PATH=./faiss_index
DATA_PATH=./data
```

## Contributing

To customize the terminal app:

1. **Add new features** in the `TerminalBrain` class
2. **Modify colors** - Edit the Rich `style` parameters
3. **Change layouts** - Use Rich `Layout` for complex UI
4. **Add animations** - Rich supports various spinners and progress bars

## License

Same as parent project

## Support

For issues:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Check Ollama connection
4. Review logs in the terminal output

---

**Happy researching with your Corporate Brain!** 🦖✨
