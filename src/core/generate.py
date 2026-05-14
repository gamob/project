import re
import requests
from langchain_ollama import OllamaLLM
import os
import logging
import time
from functools import lru_cache
from typing import Tuple

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_LLM_NUM_CTX = 4096
LLM_CONTEXT_SAFETY_MARGIN = 512

llm = OllamaLLM(
    model="qwen27b",
    base_url=OLLAMA_BASE_URL,
    temperature=0.3,
    num_ctx=DEFAULT_LLM_NUM_CTX,
    keep_alive=-1,
    num_predict=256,
    stop=["<|im_start|>", "<|im_end|>", "<think>", "Rules:"]
)

# Dedicated RAG LLM instance with no default stop tokens.
# This allows RAG answer generation and query rewriting to pass explicit
# stop boundaries without conflicting with the global default stop list.
llm_no_stop = OllamaLLM(
    model="qwen27b",
    base_url=OLLAMA_BASE_URL,
    temperature=0.3,
    num_ctx=DEFAULT_LLM_NUM_CTX,
    keep_alive=-1,
    num_predict=256,
    stop=None
)

MAX_CONTEXT_CHARS = 10_000


def _sanitize_llm_response(text: str) -> str:
    """Remove internal reasoning blocks like <think>...</think> from model output."""
    if not text:
        return text

    clean_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    if '<think>' in clean_text:
        after_think = re.search(r'</think>\s*(.*)', text, re.DOTALL)
        if after_think:
            clean_text = after_think.group(1).strip()
        else:
            clean_text = re.sub(r'<think>.*', '', text, flags=re.DOTALL).strip()

    clean_text = clean_text.replace('<think>', '').replace('</think>', '').strip()
    return clean_text


def calculate_optimal_context(query: str, max_chars: int = 10_000) -> int:
    """Adaptively calculate context size based on query complexity."""
    words = len(query.split())
    if words < 5:
        return 1500  # Short queries: minimal context
    elif words < 15:
        return 4000  # Medium queries: moderate context
    else:
        return min(max_chars, 6000)  # Long queries: cap at 6K instead of 10K


REFERENTIAL_WORDS = {
    "it", "its", "that", "this", "they", "them", "those", "these",
    "he", "she", "his", "her", "their", "there", "previous", "earlier",
    "above", "again", "more", "else", "other", "another", "same",
    "explain", "elaborate", "clarify", "expand", "simplify",
}
SHORT_QUERY_THRESHOLD = 8
GREETINGS = {"hi", "hello", "hey", "thanks", "thank", "ok", "okay", "bye", "great", "cool"}
REWRITE_TRIGGERS = {
    "how", "what", "where", "when", "why", "which",
    "install", "setup", "configure", "build", "create", "run", "execute",
    "tutorial", "guide", "help", "steps", "process", "instruction",
}


def _needs_query_rewrite(query: str) -> bool:
    """Determine if query needs rewriting for better search."""
    words = query.lower().split()
    cleaned_words = [w.strip(".,!?") for w in words]

    if all(w in GREETINGS for w in cleaned_words):
        return False
    if any(w in REWRITE_TRIGGERS for w in cleaned_words):
        return True
    if any(w in REFERENTIAL_WORDS for w in cleaned_words):
        return True
    if len(words) > SHORT_QUERY_THRESHOLD:
        return True
    return False


def check_ollama_health() -> Tuple[bool, str]:
    """Checks if the Ollama server is alive and responding."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if response.status_code == 200:
            return True, "Ollama is alive and listening! ( ◕ ◡ ◕ )"
        return False, f"Ollama returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Ollama. Is the server running?"
    except Exception as e:
        return False, f"Health check failed: {str(e)}"


@lru_cache(maxsize=256)
def _generate_search_queries_cached(query: str) -> Tuple[str, Tuple[str, ...]]:
    """Internal cached version of query generation."""
    if not _needs_query_rewrite(query):
        return (query, tuple())

    prompt = f"""Given this question, provide exactly 3 lines:
Line 1: A rewritten, clearer version of the question optimized for document search
Line 2: An alternative phrasing focusing on keywords
Line 3: Another alternative phrasing from a different angle

Return ONLY the 3 lines, no labels, no explanation, no numbering.
Do not include any reasoning tags such as <think> or </think>.

Question: {query}"""

    try:
        result = llm.invoke(prompt).strip()
        result = result.replace("<think>", "").replace("</think>", "").strip()
        lines = []
        for l in result.splitlines():
            text = l.strip()
            if not text or text.lower() in {"<think>", "</think>"}:
                continue
            text = re.sub(r'^line\s*\d+\s*:\s*', '', text, flags=re.IGNORECASE)
            lines.append(text)
        main = lines[0] if lines else query
        alts = tuple(lines[1:3]) if len(lines) > 1 else tuple()
        return (main, alts)
    except Exception:
        return (query, tuple())


def generate_search_queries(query: str) -> Tuple[str, list]:
    """Rewrites the user's question with caching support."""
    main, alts = _generate_search_queries_cached(query)
    return main, list(alts)


def extract_sources(docs: list) -> list:
    sources = []
    seen = set()
    for doc in docs:
        source = os.path.basename(doc.metadata.get("source", "Unknown"))
        page = doc.metadata.get("page", None)
        label = f"{source}"
        if page is not None:
            label += f" (Page {int(page) + 1})"
        if label not in seen:
            sources.append(label)
            seen.add(label)
    return sources


def _build_context_text(docs, query: str = "") -> str:
    """Build context text with adaptive sizing based on query complexity."""
    max_chars = calculate_optimal_context(query)
    max_chars = min(max_chars, DEFAULT_LLM_NUM_CTX - LLM_CONTEXT_SAFETY_MARGIN)
    parts = []
    total = 0
    for doc in docs:
        content = doc.page_content.strip()
        if total + len(content) > max_chars:
            if not parts:
                parts.append(content[:max_chars])
            break
        parts.append(content)
        total += len(content)
    return "\n\n".join(parts)


def build_prompt(query, docs):
    context_text = _build_context_text(docs, query)
    context_text = context_text.replace("<think>", "").replace("</think>", "")
    context_text = context_text.replace("<|im_start|>", "").replace("<|im_end|>", "")

    prompt = f"""You are a helpful assistant that answers questions based on the provided context.
Answer directly and clearly. If information is not in the context, say you don't have that information.

Context:
{context_text}

Question: {query}

Answer:"""
    
    logger.debug(f"Built prompt ({len(prompt)} chars, context={len(context_text)} chars)")
    return prompt


def answer_question(query, docs, stream=False):
    """
    Answer a question using retrieved documents.

    Returns (result, sources) where result is:
      - a generator of string chunks when stream=True
      - a plain string when stream=False
    """
    if not docs:
        logger.warning(f"answer_question called with no documents for: {query}")
        return "Không tìm thấy thông tin để trả lời câu hỏi này.", []

    try:
        sources = extract_sources(docs)
    except Exception as e:
        logger.warning(f"extract_sources failed: {e}")
        sources = []

    try:
        prompt = build_prompt(query, docs)
        logger.debug(f"Prompt built: {len(prompt)} chars")
    except Exception as e:
        logger.error(f"build_prompt failed: {e}")
        return f"⚠️ Error preparing response: {e}", sources

    try:
        t_start = time.time()

        if stream:
            # Collect all stream chunks up-front so we can inspect them.
            logger.debug(f"Starting stream for query: {query[:50]}...")
            raw_chunks = list(llm_no_stop.stream(prompt))
            full_text = "".join(raw_chunks)
            logger.debug(f"Stream returned {len(raw_chunks)} chunks, total {len(full_text)} chars")
            sanitized_text = _sanitize_llm_response(full_text)
            if not sanitized_text.strip():
                # -------------------------------------------------------
                # BUG FIX: the original code did:
                #
                #   result = llm.invoke(prompt).strip()   # string
                #   def generator_wrapper():
                #       yield result                      # ← captured by NAME
                #   result = generator_wrapper()          # ← rebinds 'result'!
                #
                # Because Python closures capture variables by reference, not
                # value, `generator_wrapper` would yield the *generator object*
                # itself (the new value of `result`) instead of the string.
                # Fix: store the invoke result under a different name so the
                # closure captures the correct value.
                # -------------------------------------------------------
                logger.warning("Stream returned empty, falling back to invoke()")
                invoke_text = _sanitize_llm_response(llm_no_stop.invoke(prompt).strip())
                logger.debug(f"invoke() returned {len(invoke_text)} chars")

                # Check if invoke also returned empty - indicates LLM/server issue
                if not invoke_text:
                    logger.error("Both stream() and invoke() returned empty responses. LLM server may not be responding correctly.")
                    logger.debug(f"Prompt sent was ({len(prompt)} chars): {prompt[:100]}...")
                    error_msg = "⚠️ The language model server did not generate a response. Please verify Ollama is running and the model is properly loaded."
                    def error_generator():
                        yield error_msg
                    result = error_generator()
                else:
                    def generator_wrapper():
                        yield invoke_text          # ← correct: captures invoke_text

                    result = generator_wrapper()

            else:
                collected = [sanitized_text] if sanitized_text != full_text else raw_chunks

                def chunk_generator():
                    for chunk in collected:
                        yield chunk

                result = chunk_generator()

        else:
            invoke_text = _sanitize_llm_response(llm_no_stop.invoke(prompt).strip())
            if not invoke_text:
                logger.warning("invoke() returned empty response, falling back to stream()")
                raw_chunks = list(llm_no_stop.stream(prompt))
                invoke_text = _sanitize_llm_response("".join(raw_chunks).strip())
                logger.debug(f"Fallback stream returned {len(raw_chunks)} chunks, total {len(invoke_text)} chars")
                if not invoke_text:
                    logger.error("Both invoke() and stream() returned empty responses. LLM server may not be responding correctly.")
                    invoke_text = "⚠️ The language model server did not generate a response. Please verify Ollama is running and the model is properly loaded."

            result = invoke_text

        elapsed = time.time() - t_start
        logger.debug(f"LLM call finished: {elapsed:.3f}s (stream={stream})")

        return result, sources

    except Exception as e:
        logger.error(f"LLM invocation failed: {e}", exc_info=True)
        
        # Determine error message
        if "CUDA" in str(e) or "memory" in str(e).lower():
            error_text = "⚠️ Server memory issue. Please try again."
        elif "timeout" in str(e).lower():
            error_text = "⚠️ Request timed out. Please try with a simpler question."
        else:
            error_text = f"⚠️ Could not generate response: {str(e)[:100]}"
        
        # Return appropriate format based on streaming mode
        if stream:
            def error_gen():
                yield error_text
            return error_gen(), sources
        else:
            return error_text, sources
