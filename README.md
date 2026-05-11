# Corporate Brain v1.0

A local, air-gapped Retrieval-Augmented Generation (RAG) system built with Streamlit, LangChain, FAISS, BM25, and Ollama.

## Overview

This project is designed for secure document search and question answering over enterprise content without sending data to external services. Note that its being tested and used on a server with 96 cores cpu and dual a2 setup.

- Hybrid retrieval using semantic embeddings + BM25 keyword matching
- Reciprocal Rank Fusion (RRF) for stronger search ranking
- Cross-encoder reranking to refine final results
- Session-aware conversation context for multi-turn RAG
- Streamlit UI for chat-style document interaction
- SQLite-based chat history storage

## Key Components

- `src/core/brain_service.py` — central orchestrator for index lifecycle and search
- `src/core/retrieve.py` — hybrid retrieval engine with BM25 + FAISS search
- `src/core/hybrid_search_config.py` — RRF config and hybrid fusion tuning
- `src/core/generate.py` — Ollama prompt construction and query rewriting
- `src/core/conversation_context.py` — multi-turn follow-up handling
- `src/ui/app.py` — Streamlit interface for interactive chat
- `src/storage/chat_store.py` — persistent session and message storage

## Getting Started

1. Install dependencies from `requirements.txt`
2. Place documents into the `data/` folder
3. Run the Streamlit app:

```bash
streamlit run src/ui/app.py
```

4. Upload documents in the sidebar, then click `Sync Brain`
5. Ask questions in the chat interface

## Why this project

This repository is built to support offline, private document intelligence for teams that cannot rely on cloud-based AI services. It balances semantic search with keyword retrieval and adds session memory for better follow-up answers.

## Notes

- Uses local Ollama model integration
- Designed for Vietnamese/English query support
- Works best when document files are kept in `data/`

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
