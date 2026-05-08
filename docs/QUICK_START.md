# 🚀 Quick Start Checklist

Follow these steps to get your terminal RAG app running on your GPU server.

## ✅ Pre-Flight Check

- [ ] Python 3.8+ installed
- [ ] GPU drivers installed and working
- [ ] Ollama installed and working
- [ ] Git or project files downloaded

## 📦 Installation (5 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
⏱️ Expected: 2-3 minutes

**Alternative (minimal):**
```bash
pip install rich langchain langchain-community langchain-ollama faiss-cpu bm25s sentence-transformers
```

### Step 2: Verify Ollama
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running:
ollama serve
```
✓ Should return JSON with installed models

### Step 3: Have a Model Ready
```bash
# Check installed models
ollama list

# Pull a model if needed (example: 13B)
ollama pull llama2:13b

# Or for GPU: pull larger model
ollama pull llama2:70b
```
⏱️ Expected: 5-30 minutes depending on model size

## 🚀 Launch App

### Windows
```bash
run_terminal.bat
```

### Linux/Mac
```bash
# Easy way (recommended):
chmod +x run_terminal.sh
./run_terminal.sh

# Or directly:
cd src
python3 app_terminal.py
```

**Note on Linux servers:** If you see tons of "missing ScriptRunContext" warnings, use the launcher script above — it suppresses them automatically. See Troubleshooting section in TERMINAL_README.md for more info.

✓ You should see:
```
🦖 Corporate Brain v1.0
Local • Secure • Air-gapped AI Assistant

✓ Ollama Connected
✓ Brain Connected! (FAISS + BM25)

[Menu with options 1-6]
```

## 🧠 First Time Usage

### 1️⃣ Upload Documents
- **Menu:** Option 2 (📂 Manage Documents)
- **Choice:** 1 (Upload new document)
- **Enter:** Full path to your document
- **Examples:**
  - `C:\Users\You\Documents\report.pdf`
  - `/home/user/documents/file.txt`
  - `~/Desktop/data.xlsx`

### 2️⃣ Sync Brain
- **Menu:** Option 3 (🔄 Sync Brain)
- **Wait:** Progress indicator
- **Result:** ✓ Brain synced successfully!

⏱️ Expected time depends on:
- Document size: 100MB = ~2-5 min
- Model speed: GPU models faster
- First run: Always slower

### 3️⃣ Start Chatting
- **Menu:** Option 1 (💬 Chat)
- **Type:** Your question
- **Press:** Enter
- **Wait:** AI responds with streamed output
- **See:** Confidence score + sources
- **Type:** `exit` to return to menu

## 💡 Pro Tips

### Remote GPU Server

```bash
# Connect
ssh user@gpu-server

# Quick start
cd ~/project
python src/app_terminal.py

# Or use tmux (persistent)
tmux new-session -s brain
python src/app_terminal.py
# Press Ctrl+B, D to detach
# Later: tmux attach -t brain
```

### Performance

- **First query:** Wait 30-120s (model loading)
- **Later queries:** 2-15s
- **Multiple models:** Keep running app, don't restart
- **Out of memory:** Use smaller model (mistral:7b)

### Document Tips

- 📄 **PDF:** Works well with OCR-able PDFs
- 📝 **TXT/MD:** Best format
- 📘 **DOCX:** Supported
- 📊 **Excel/CSV:** Converted to text
- 🎤 **PowerPoint:** Supported

**Max size:** Depends on available RAM/VRAM
- Small docs: <10MB ✓ Instant
- Medium docs: 10-100MB (2-5 min)
- Large docs: >100MB (10+ min, need more VRAM)

## 🔧 Troubleshooting

### "Ollama not connected"
```bash
# In another terminal:
ollama serve

# Or check:
curl http://localhost:11434/api/tags
```

### "No documents found"
1. Check: Is `data/` folder created?
2. Check: Did you upload files?
3. Fix: Upload documents (Menu → 2 → 1)
4. Sync: Click "Sync Brain" (Menu → 3)

### First Query Takes Too Long
- ✓ Normal! Model is loading (~60s on first query)
- Subsequent queries will be 5-15s
- Keep app running to avoid reload
- Larger models take longer

### Terminal Looks Garbled
- Your terminal doesn't support ANSI colors
- Fix: Use modern terminal (Windows Terminal, iTerm2, etc.)
- Or: Restart terminal after first run

### "Python not found" (Windows)
```bash
# Make sure Python is in PATH
python --version

# Or use full path:
C:\Python39\Scripts\python.exe app_terminal.py
```

## 📚 Documentation

After getting started, check these for more info:

1. **MIGRATION_GUIDE.md** - Switching from web app
2. **TERMINAL_README.md** - Complete documentation
3. **TERMINAL_CONFIG_GUIDE.md** - Advanced configuration
4. **TERMINAL_UI_PREVIEW.md** - What the UI looks like

## 🎯 Goals

### Basic (Today)
- [ ] Install dependencies
- [ ] Run app
- [ ] Upload 1-2 documents
- [ ] Chat with them

### Intermediate (This Week)
- [ ] Set up on GPU server
- [ ] Use tmux for persistent sessions
- [ ] Organize document library
- [ ] Save useful chat sessions

### Advanced (Next Week)
- [ ] Optimize for larger models
- [ ] Tune search parameters
- [ ] Integrate with workflows
- [ ] Set up monitoring

## 🆘 Help & Support

### Quick Answers
- **What's different from web app?** → See MIGRATION_GUIDE.md
- **How to configure?** → See TERMINAL_CONFIG_GUIDE.md
- **What does it look like?** → See TERMINAL_UI_PREVIEW.md
- **Full docs?** → See TERMINAL_README.md

### Common Commands

```bash
# Start app
python src/app_terminal.py

# Start Ollama (if not running)
ollama serve

# Check Ollama models
ollama list

# Pull a model
ollama pull mistral:7b

# Check GPU status
nvidia-smi

# Monitor GPU live
watch nvidia-smi
```

## 🎉 You're Ready!

```
1. Install: pip install -r requirements.txt
2. Start Ollama: ollama serve
3. Run app: python src/app_terminal.py
4. Upload docs: Menu → 2 → 1
5. Sync brain: Menu → 3
6. Chat: Menu → 1
7. Enjoy! 🦖
```

---

**Everything working? Awesome! 🎊**

**Have questions?** Check the documentation files or the in-app help text.

**Want to customize?** See TERMINAL_CONFIG_GUIDE.md for advanced setup.

**Happy RAGing! 🚀**
