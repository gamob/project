"""
prep_questions.py — Generate and save evaluation questions independently.

Run this once (or whenever your data changes) to build the question bank.
The saved file is reused by generate_evals.py so you don't regenerate every run.

Usage:
    python prep_questions.py              # generate 200 raw questions using the default Ollama URL
    python prep_questions.py --review     # print existing questions and exit
    python prep_questions.py --ollama-url http://server:11434  # use remote Ollama if needed
    OLLAMA_BASE_URL=http://server:11434 python prep_questions.py  # env var
"""

import json
import logging
import os
import re
import random
import argparse
import time
from ..core.brain_service import Brain

logger = logging.getLogger(__name__)
# from generate import llm as rag_llm  # Removed - using local instance now

# Allow configurable Ollama URL
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

def get_rag_llm(base_url=None):
    """Get configured RAG LLM instance with the same settings as generate.py."""
    url = base_url or OLLAMA_BASE_URL
    try:
        from langchain_ollama import OllamaLLM
        # For JSON generation, prevent reasoning blocks and premature termination
        return OllamaLLM(
            model="qwen27b",
            base_url=url,
            temperature=0.1,
            num_ctx=2048,       # /no_think responses are short; 2k ctx is plenty
            num_thread=64,
            keep_alive=-1,
            repeat_penalty=1.2,
            # /no_think suppresses the think block — JSON is 60-150 tokens, 512 is safe
            num_predict=512,
            stop=["<|im_start|>", "<|im_end|>"],
            timeout=25,         # Hard wall-clock timeout — prevents infinite freeze
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM: {e}")
        logger.error(f"Make sure Ollama is running at: {url}")
        logger.error("Set OLLAMA_BASE_URL environment variable or use --ollama-url")
        raise


def _is_network_error(error_text: str) -> bool:
    normalized = error_text.lower()
    return any(token in normalized for token in [
        'temporary failure in name resolution',
        'name or service not known',
        'connection refused',
        'failed to establish a new connection',
        'getaddrinfo failed',
        'dns',
        'socket.gaierror',
    ])

# ── Paths ─────────────────────────────────────────────────────────────────────
EVAL_DIR   = "evaluation"
DATA_FILE  = os.path.join(EVAL_DIR, "eval_dataset.jsonl")
NUM_QUESTIONS = 200
os.makedirs(EVAL_DIR, exist_ok=True)

# ── Question types — varied and progressively harder ─────────────────────────
# Each type targets a different cognitive level so the bank is balanced.
QUESTION_TYPES = [
    # Factual recall — straightforward but must be specific
    "a factual question about a specific number, percentage, or measurement mentioned",
    # Process understanding
    "a 'how does X work' process question requiring a 2-3 step answer",
    # Cause and effect
    "a 'why' cause-and-effect question where the reason is explicitly stated",
    # Comparison or distinction
    "a question comparing or distinguishing two specific concepts, systems, or roles mentioned",
    # Condition / requirement
    "a question about what conditions, requirements, or criteria must be met for something",
    # Consequence
    "a question about what happens as a result or consequence of a specific action or event",
]

# ── Chunk quality ─────────────────────────────────────────────────────────────
MIN_CHUNK_CHARS = 200
MIN_CHUNK_SCORE = 5

JUNK_CHUNK_PATTERNS = [
    re.compile(r"(ky ten|chu ky|nguoi ky|da ky|signature|signed by)",    re.IGNORECASE),
    re.compile(r"(tong giam doc|giam doc|truong phong).{0,60}$",         re.IGNORECASE | re.MULTILINE),
]

_VERB_PAT  = re.compile(
    r"(la|duoc|co|se|phai|can|thuc hien|cho phep|giup"
    r"|is|are|was|were|can|will|must|should|allows|provides"
    r"|enables|requires|performs|returns|defines|describes)",
    re.IGNORECASE
)
_CODE_PAT  = re.compile(r"\b[A-Z]{2,}\d{2,}|\b\d{2}/\d{2}/\d{4}\b")
_UPPER_PAT = re.compile(r"\b[A-Z]{4,}\b")


def _chunk_score(text: str) -> int:
    words = text.split()
    n = len(words)
    if n == 0:
        return 0
    score = 0
    if len(text.strip()) >= MIN_CHUNK_CHARS:                   score += 1
    if n >= 25:                                                 score += 1
    if _VERB_PAT.search(text):                                 score += 1
    if len(set(w.lower() for w in words)) / n >= 0.45:        score += 1
    if len(_UPPER_PAT.findall(text)) / max(n, 1) < 0.20:     score += 1
    if len(_CODE_PAT.findall(text)) <= 2:                      score += 1
    if re.search(r"[.,:;!?]", text):                           score += 1
    return score


def _is_junk_chunk(text: str) -> bool:
    for pat in JUNK_CHUNK_PATTERNS:
        if pat.search(text):
            return True
    return _chunk_score(text) < MIN_CHUNK_SCORE


# ── Question blacklist ────────────────────────────────────────────────────────
BLACKLISTED_STEMS = [
    re.compile(r"^(ai|who).{0,40}(ký|sign)",                            re.IGNORECASE),
    re.compile(r"(ngày|date|khi nào|when).{0,40}(ký|sign)",             re.IGNORECASE),
    re.compile(r"(chữ ký|signature|signing|ký tên|ký vào|ký duyệt)",    re.IGNORECASE),
    re.compile(r".{0,30}(signing|ký).{0,30}(document|tài liệu|văn bản)", re.IGNORECASE),
    re.compile(r"(leave|nghỉ phép|ngày nghỉ).{0,30}(date|ngày|of)",     re.IGNORECASE),
    re.compile(r"(bao nhiêu lần|how many times|repeated|lặp lại)",       re.IGNORECASE),
    re.compile(r"(repeating pattern|pattern in this|repetition in)",     re.IGNORECASE),
    re.compile(r"^what is this document",                                re.IGNORECASE),
    re.compile(r"(how many pages|bao nhiêu trang)",                      re.IGNORECASE),
    re.compile(r"^what date is mentioned",                               re.IGNORECASE),
    re.compile(r"^(tên|name).{0,20}(người|person|ai|who)",              re.IGNORECASE),
    re.compile(r"^who is [a-z\s]+\??\s*$",                              re.IGNORECASE),
    re.compile(r"(bạn có nghĩ|do you think|bạn cảm thấy)",              re.IGNORECASE),
    re.compile(r"(json|format|trả về|return).{0,30}(object|chuỗi)",     re.IGNORECASE),
    re.compile(r"(prompt|system prompt|llm|model output)",               re.IGNORECASE),
    re.compile(r"^what is the name of (this|the) (algorithm|document)",  re.IGNORECASE),
    re.compile(r"^what is (step \d|responsible for)",                    re.IGNORECASE),
    # Trivial code examples (real names of sports people are from code sample chunks)
    re.compile(r"(LaMarcus|Aldridge|Tony Parker|getUserById|createUser)", re.IGNORECASE),
    re.compile(r"^what type of (data|structure) does .{0,20}(represent|provide)", re.IGNORECASE),
    re.compile(r"how many (parameters|gpu|lines).{0,20}(does|were|has)",  re.IGNORECASE),
]


def _is_blacklisted(question: str) -> bool:
    return any(pat.search(question) for pat in BLACKLISTED_STEMS)


def _extract_keywords(text: str) -> frozenset:
    stopwords = {
        "la", "cua", "va", "co", "the", "a", "an", "is", "are",
        "in", "of", "to", "what", "who", "how", "why", "when",
    }
    words = {w.lower().strip("?.,") for w in text.split() if len(w) > 3}
    return frozenset(words - stopwords)

def _extract_json(text: str) -> dict:
    """
    Specifically handles Qwen/Ollama 'thinking' blocks and conversational filler.
    Also handles truncated responses where </think> is missing.
    """
    # 1. Strip complete <think>...</think> blocks
    clean_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # 2. If <think> is still present (unclosed — model was truncated mid-thought),
    #    try to grab JSON from after </think> in the original text first,
    #    then fall back to stripping everything from <think> onward.
    if '<think>' in clean_text:
        after_think = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if after_think:
            clean_text = after_think.group(1).strip()
        else:
            # No </think> at all — strip from <think> to end, nothing useful after it
            clean_text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()

    # 3. Look for the JSON block { ... }
    match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
    
    if match:
        json_candidates = match.group(1)
        try:
            # Try a direct parse
            return json.loads(json_candidates)
        except json.JSONDecodeError:
            # 3. Last-ditch effort: manually find question/answer keys 
            # if the model messed up commas or quotes
            q = re.search(r'"question":\s*"(.*?)"', json_candidates, re.DOTALL)
            a = re.search(r'"answer":\s*"(.*?)"', json_candidates, re.DOTALL)
            if q and a:
                return {
                    "question": q.group(1).strip(),
                    "answer": a.group(1).strip()
                }
    
    # If we get here, the model really didn't provide what we needed
    raise ValueError(f"Brain Glitch: No JSON found in response. Head: {text[:50]}...")


def _is_answerable(question: str, expected_answer: str, brain) -> bool:
    """Fast answerability check using FAISS only (no reranker)."""
    try:
        raw_docs = brain.vector_store.similarity_search(question, k=6)
        if not raw_docs:
            return False
        combined = " ".join(d.page_content.lower() for d in raw_docs)
        answer_words = [w.lower().strip("?.,") for w in expected_answer.split() if len(w) > 2]
        if not answer_words:
            return False
        hits = sum(1 for w in answer_words if w in combined)
        return hits / len(answer_words) >= 0.5
    except Exception:
        return True


# ── Core generation ───────────────────────────────────────────────────────────
# ── Direct Ollama HTTP caller (bypasses LangChain wrapper) ───────────────────
# We call /api/generate directly so we control every parameter precisely.
# "think: false" was removed — it requires Ollama ≥0.6.x and silently hangs
# on older versions. Instead we suppress thinking via prompt + format.

_OLLAMA_MODEL    = "qwen27b"
_OLLAMA_BASE_URL = OLLAMA_BASE_URL

def _check_ollama_version() -> tuple[int, int]:
    """Return (major, minor) Ollama version. Returns (0,0) on failure."""
    import requests as _req
    try:
        r = _req.get(f"{_OLLAMA_BASE_URL}/api/version", timeout=5)
        v = r.json().get("version", "0.0.0")          # e.g. "0.6.2"
        parts = [int(x) for x in v.split(".")[:2]]
        return tuple(parts) if len(parts) == 2 else (0, 0)
    except Exception:
        return (0, 0)

_OLLAMA_SUPPORTS_THINK: bool | None = None   # cached after first call

def _call_ollama_direct(prompt: str, timeout: int = 120) -> str | None:
    """
    POST to /api/generate. Disables thinking when Ollama supports it;
    falls back to prompt-only suppression on older versions.
    timeout=120: with 3 workers on a single GPU, each request can sit in
    Ollama's queue ~3× longer than single-threaded (~20s → budget 90s+).
    """
    import requests as _req
    global _OLLAMA_SUPPORTS_THINK

    if _OLLAMA_SUPPORTS_THINK is None:
        major, minor = _check_ollama_version()
        _OLLAMA_SUPPORTS_THINK = (major, minor) >= (0, 6)
        flag = "✅ think=false supported" if _OLLAMA_SUPPORTS_THINK else "⚠️  think=false NOT supported (Ollama <0.6) — using prompt suppression"
        logger.info(f"  🔍 Ollama version check: {flag}")

    payload: dict = {
        "model":  _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",          # sampler-level JSON mode — works on all versions
        "options": {
            "temperature":    0.1,
            "num_predict":    600,  # enough for any JSON response
            "repeat_penalty": 1.2,
            "num_thread":     64,
            "stop":           ["<|im_start|>", "<|im_end|>"],
        },
    }
    if _OLLAMA_SUPPORTS_THINK:
        payload["think"] = False   # suppress reasoning block natively

    try:
        resp = _req.post(
            f"{_OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except _req.exceptions.Timeout:
        logger.warning("  ⏱️  Ollama call timed out — skipping chunk")
        return None
    except Exception as e:
        err = str(e)
        if "connection" in err.lower() or "refused" in err.lower():
            logger.warning(f"  🔌 Ollama connection error: {err[:60]}")
            return None
        raise


def _generate_one(args):
    """
    Generate a single Q&A pair from a chunk.
    Uses direct Ollama HTTP API (think=false) instead of LangChain wrapper.
    Returns a record dict on success, or None if the chunk should be skipped.
    """
    doc, _llm_unused, attempt_num = args
    chunk = doc.page_content[:700]
    title = doc.metadata.get("doc_title", "unknown document")
    c_idx = doc.metadata.get("chunk_index", "?")
    c_tot = doc.metadata.get("total_chunks", "?")

    prompt = (
        "Output ONLY a raw JSON object with exactly two keys.\n\n"
        '{"question": "A specific question answered by this section", '
        '"answer": "2-3 sentence answer using only this context"}\n\n'
        f"Document: {title} | Section {c_idx}/{c_tot}\n---\n{chunk}\n---\n"
        "Output the JSON object now. Start with { immediately."
    )

    for attempt in range(2):
        try:
            raw = _call_ollama_direct(prompt)
            if raw is None:
                return None
            res = raw.strip()
            if len(res) < 10:
                continue
            # Safety strip in case model still emits a think block somehow
            res = re.sub(r'<think>.*?</think>', '', res, flags=re.DOTALL).strip()
            parsed   = _extract_json(res)
            question = parsed.get("question", "").strip()
            answer   = parsed.get("answer",   "").strip()
            if question and answer:
                return {"question": question, "answer": answer,
                        "source": title, "chunk": c_idx}
        except Exception as e:
            if attempt == 0:
                logger.warning(f"  ⚠️  Parse error (will retry): {str(e)[:80]}")
    return None


def generate_questions(brain, llm, num=NUM_QUESTIONS, output_file=DATA_FILE,
                       workers=3):
    """
    Generate questions in parallel using a thread pool.

    workers=3 not 6: Ollama serves a single GPU sequentially. With 6 workers,
    each request waits in queue ~6x longer than single-threaded (~20s → 120s),
    which caused the timeout storm. 3 workers hides network latency without
    blowing past the 120s request timeout.
    """
    from concurrent.futures import as_completed, ThreadPoolExecutor
    import threading

    logger.info(f"🚀 Generating {num} questions (workers={workers})...")
    t0 = time.time()

    all_docs  = list(brain.vector_store.docstore._dict.values())
    good_docs = [d for d in all_docs if not _is_junk_chunk(d.page_content)]
    logger.info(f"  📦 {len(all_docs)} total chunks → {len(good_docs)} question-worthy")
    if not good_docs:
        logger.error("❌ No suitable chunks found.")
        return

    scores  = [_chunk_score(d.page_content) for d in good_docs]
    weights = [s * s for s in scores]

    # Pre-sample enough docs to satisfy num with expected rejection rate
    MAX_ATTEMPTS = num * 8
    sample_size  = min(MAX_ATTEMPTS, len(good_docs) * 6)
    doc_pool     = random.choices(good_docs, weights=weights, k=sample_size)

    # Cache for _is_answerable to avoid redundant FAISS searches
    _answerable_cache: dict = {}
    _cache_lock = threading.Lock()

    def is_answerable_cached(question, answer):
        key = question[:80]
        with _cache_lock:
            if key in _answerable_cache:
                return _answerable_cache[key]
        result = _is_answerable(question, answer, brain)
        with _cache_lock:
            _answerable_cache[key] = result
        return result

    seen_keywords: list = []
    count    = 0
    rejected = 0

    with open(output_file, "w", encoding="utf-8") as f:
        # Submit ALL jobs as a list — as_completed() snapshots once and is stable
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_generate_one, (doc, llm, i))
                       for i, doc in enumerate(doc_pool)]

            for future in as_completed(futures):
                if count >= num:
                    # Cancel everything still pending so shutdown() returns fast
                    for f in futures:
                        f.cancel()
                    break

                try:
                    record = future.result()
                except Exception as e:
                    logger.error(f"  💥 Worker crashed: {e}")
                    rejected += 1
                    continue

                if record is None:
                    rejected += 1
                    continue

                question = record["question"]
                answer   = record["answer"]

                if _is_blacklisted(question):
                    rejected += 1
                    continue

                kw = _extract_keywords(question)
                if any(len(kw & seen) / max(len(kw), 1) > 0.6 for seen in seen_keywords):
                    rejected += 1
                    continue

                if not is_answerable_cached(question, answer):
                    rejected += 1
                    continue

                seen_keywords.append(kw)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                count += 1

                if count % 5 == 0:
                    elapsed = time.time() - t0
                    rate    = count / elapsed * 60
                    logger.info(f"  ✍️  {count}/{num} questions  "
                                f"({elapsed:.0f}s elapsed, {rate:.1f} q/min)")

    elapsed = time.time() - t0
    logger.info(f"  ✅ Done — {count} questions saved to '{output_file}' in {elapsed:.0f}s")
    logger.info(f"     ({len(doc_pool)} attempts total, {rejected} rejected)")
def review_questions(input_file=DATA_FILE):
    """Print all saved questions for manual review."""
    if not os.path.exists(input_file):
        logger.error(f"❌ No question file found at '{input_file}'. Run without --review first.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    logger.info(f"\n📋 {len(lines)} saved questions:\n{'='*60}")
    for i, line in enumerate(lines, 1):
        try:
            d = json.loads(line)
            logger.info(f"\nQ{i}  [{d.get('source','?')} §{d.get('chunk','?')}]")
            logger.info(f"     Q: {d['question']}")
            logger.info(f"     A: {d['answer'][:120]}{'...' if len(d['answer'])>120 else ''}")
        except Exception:
            logger.warning(f"Q{i}: [malformed]")
    logger.info("="*60)


def main():
    parser = argparse.ArgumentParser(description="Generate RAG evaluation questions.")
    parser.add_argument("--review", action="store_true",
                        help="Print existing questions and exit (no generation)")
    parser.add_argument("--num", type=int, default=NUM_QUESTIONS,
                        help=f"Number of questions to generate (default {NUM_QUESTIONS})")
    parser.add_argument("--out", type=str, default=DATA_FILE,
                        help="Output file path")
    parser.add_argument("--ollama-url", type=str, default=None,
                        help=f"Ollama server URL (default: {OLLAMA_BASE_URL})")
    args = parser.parse_args()

    if args.review:
        review_questions(args.out)
    else:
        # Clean up old files before starting
        if os.path.exists(args.out):
            os.remove(args.out)
            logger.info(f"🗑️  Removed existing file: {args.out}")

        brain = Brain()
        logger.info("🔄 Syncing indices...")
        brain.sync_indices()

        # Point the direct Ollama caller at the right server
        ollama_url = args.ollama_url or OLLAMA_BASE_URL
        import prep_questions as _self
        _self._OLLAMA_BASE_URL = ollama_url
        logger.info(f"🔌 Using Ollama at: {ollama_url} (model: {_OLLAMA_MODEL})")

        # Generate raw questions (no polishing)
        rag_llm = get_rag_llm(ollama_url)
        generate_questions(brain, rag_llm, num=args.num, output_file=args.out)
        logger.info("\n✅ Raw questions generated (unpolished - preserves natural human-like quality)")

        logger.info("\n👀 Preview of generated questions:")
        review_questions(args.out)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )
    main()
