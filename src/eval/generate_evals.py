"""
generate_evals.py — Phase 2 (RAG inference) + Phase 3 (judge & report) + Faithfulness Check.

Questions are loaded from evaluation/eval_test.jsonl, eval_train.jsonl, or eval_valid.jsonl
(created by merge_eval_datasets.py).

Features:
- Hybrid RAG retrieval with configurable fusion strategies
- LLM-based semantic judging (correct/partial/wrong)
- Faithfulness evaluation (answer grounding in source documents)

Usage:
    python generate_evals.py                           # default: uses eval_test.jsonl (all questions)
    python generate_evals.py --dataset test            # uses eval_test.jsonl
    python generate_evals.py --dataset train           # uses eval_train.jsonl
    python generate_evals.py --dataset valid           # uses eval_valid.jsonl
    python generate_evals.py --dataset test --sample 5 # test with random 5 questions
"""
import logging
import random
import json
import os
import re
import time
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..core.brain_service import Brain
from ..core.generate import answer_question
from langchain_ollama import OllamaLLM
from ..core.faithfulness_check import evaluate_answer_faithfulness

logger = logging.getLogger(__name__)


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.getLogger().setLevel(level)

# ── Paths ─────────────────────────────────────────────────────────────────────
EVAL_DIR     = "evaluation"


def get_data_file(dataset_type="test"):
    """Get the appropriate eval dataset file based on type.
    
    Args:
        dataset_type: One of 'test', 'train', or 'valid'
    
    Returns:
        Path to the eval dataset file
    """
    if dataset_type not in ["test", "train", "valid"]:
        dataset_type = "test"
    return os.path.join(EVAL_DIR, f"eval_{dataset_type}.jsonl")


# ── Concurrency & timeouts ────────────────────────────────────────────────────
PHASE2_WORKERS  = 1     # overlap reranking with LLM wait time
PHASE3_WORKERS  = 1     # 27B model: serialise judge calls, no queue overhead
PHASE2_TIMEOUT  = 1000  # seconds per question
PHASE3_TIMEOUT  = 1000  # seconds per question

# ── Judge LLM (use fast model — 8B is enough for semantic comparison) ─────────
judge_llm = OllamaLLM(
    model="local-llama3.1",
    base_url="http://localhost:11434",
    temperature=0.0,
    num_ctx=4096,
)


# ── Shared helper ─────────────────────────────────────────────────────────────
def _extract_json(text: str) -> dict:
    """Robustly extract a JSON object from LLM output."""
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # If the output contains extra text around the JSON, try to recover the first valid object.
    for start_match in re.finditer(r"\{", text):
        depth = 0
        for idx in range(start_match.start(), len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            if depth == 0:
                candidate = text[start_match.start() : idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    break

    # Last resort: attempt to clean up a single object block and parse it.
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = re.sub(r",\s*([}\]])", r"\1", match.group())
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No JSON found: {text[:200]}")


# ── PHASE 2: RAG Inference ────────────────────────────────────────────────────
def _answer_one(item):
    """Answer one question. Returns (idx, data) or (idx, None) on error."""
    idx, data, brain = item
    try:
        logger.info(f"  ⏳ Starting Q{idx+1}: {data['question'][:100]}")
        docs, _, confidence_pct = brain.search(data["question"])
        logger.info(f"  🔎 Search returned {len(docs)} docs for Q{idx+1}")
        rag_answer, sources = answer_question(
            data["question"], 
            docs,
            confidence=confidence_pct / 100.0  # Convert percentage to decimal (0-1)
        )
        data["rag_answer"] = rag_answer
        
        # NEW: Evaluate faithfulness of the answer
        faithfulness_result = evaluate_answer_faithfulness(rag_answer, docs)
        data["faithfulness"] = faithfulness_result
        
        src_label = f" [{sources[0]}]" if sources else ""
        logger.info(f"\n  Q{idx+1}{src_label}: {data['question'][:80]}")
        logger.info(f"  💬 {rag_answer[:200]}{'...' if len(rag_answer) > 200 else ''}")
        logger.info(f"  🔍 Faithfulness: {faithfulness_result['confidence_level']} ({faithfulness_result['overall_score']:.2f})")
        return idx, data
    except Exception as e:
        logger.error(f"  ❌ Q{idx+1} error: {e}")
        return idx, None


def run_rag_inference(brain, args, data_file, rag_answers):
    # Update the print to show whether we are running a subset or all questions
    if args.sample is not None and args.sample > 0:
        logger.info(f"🤖 Phase 2: Answering (Random {args.sample} of {PHASE2_WORKERS} workers, timeout={PHASE2_TIMEOUT}s)...")
    else:
        logger.info(f"🤖 Phase 2: Answering (All questions with {PHASE2_WORKERS} workers, timeout={PHASE2_TIMEOUT}s)...")
    t0 = time.time()

    # 1. Load ALL available questions from the file first[cite: 2]
    all_raw_data = []
    with open(data_file, "r", encoding="utf-8") as fin:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                all_raw_data.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"  ⚠️  Malformed line skipped: {line[:50]}...")

    # 2. Randomly select N questions or use all if sample is 0 or negative
    if args.sample is not None and args.sample > 0:
        num_to_test = min(args.sample, len(all_raw_data))
        selected_questions = random.sample(all_raw_data, num_to_test)
        logger.info(f"  🎲 Randomly selected {num_to_test} questions for this test run.")
    else:
        num_to_test = len(all_raw_data)
        selected_questions = all_raw_data
        logger.info(f"  📊 Using all {num_to_test} questions from {args.dataset} dataset.")

    # 3. Prepare the items for processing[cite: 2]
    # We use enumerate so we can track the index for the results list[cite: 2]
    items = [(i, data, brain) for i, data in enumerate(selected_questions)]

    # 4. Execute the threads for just these 5 questions[cite: 2]
    results = [None] * len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=PHASE2_WORKERS) as pool:
        futures = {pool.submit(_answer_one, item): item[0] for item in items}
        for future in as_completed(futures, timeout=PHASE2_TIMEOUT):
            try:
                idx, data = future.result(timeout=PHASE2_TIMEOUT)
            except Exception as e:
                idx = futures[future]
                logger.error(f"  💥 Q{idx+1} crashed: {e}")
                done += 1
                continue
            results[idx] = data
            done += 1
            # Updated progress print[cite: 2]
            if done == len(items):
                logger.info(f"  ✅ {done}/{len(items)} answered")

    # 5. Save only the answered questions to the RAG_ANSWERS file[cite: 2]
    count = 0
    with open(rag_answers, "w", encoding="utf-8") as fout:
        for data in results:
            if data is not None:
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                count += 1

    logger.info(f"\n🎉 Phase 2 done — {count}/{len(items)} answered in {time.time()-t0:.1f}s")


# ── PHASE 3: Judge & Report ───────────────────────────────────────────────────
def _judge_one(item):
    """Judge one Q&A pair. Returns (idx, data_with_score) or (idx, None)."""
    idx, data = item
    prompt = (
        "You are a semantic evaluator. Judge whether the model answer conveys "
        "the same meaning as the expected answer.\n"
        "Return ONLY a raw JSON object — no text outside it.\n\n"
        f"Question: {data['question']}\n"
        f"Expected answer: {data['answer']}\n"
        f"Model answer: {data['rag_answer']}\n\n"
        "Scoring guide:\n"
        "  2 = Correct: same meaning, even if wording or language differs\n"
        "  1 = Partial: right idea but missing one important detail\n"
        "  0 = Wrong: factually incorrect, irrelevant, or could not find the answer\n\n"
        "Do NOT mark wrong for extra words, different phrasing, or different language"
        " — judge MEANING only.\n\n"
        'Return exactly: {"score": 2, "reason": "brief explanation"}'
    )
    try:
        res = judge_llm.invoke(prompt)
        result = _extract_json(res)
        result["score"] = int(result.get("score", 0))
        data.update(result)

        faith_score = data.get("faithfulness", {}).get("overall_score", 0.5)
        judge_norm = result["score"] / 2.0
        combined_score = 0.7 * judge_norm + 0.3 * faith_score
        data["combined_score"] = float(combined_score)

        if combined_score >= 0.85:
            data["combined_judgement"] = 2
        elif combined_score >= 0.6:
            data["combined_judgement"] = 1
        else:
            data["combined_judgement"] = 0

        return idx, data
    except Exception as e:
        logger.error(f"  ⚠️  Judge failed on Q{idx+1}: {e}")
        return idx, None


def run_judge_and_report(rag_answers, final_report):
    logger.info(f"⚖️  Phase 3: Grading ({PHASE3_WORKERS} worker, timeout={PHASE3_TIMEOUT}s)...\n")
    t0 = time.time()

    items = []
    with open(rag_answers, "r", encoding="utf-8") as fin:
        for i, line in enumerate(fin):
            line = line.strip()
            if not line:
                continue
            try:
                items.append((i, json.loads(line)))
            except json.JSONDecodeError:
                logger.warning(f"  ⚠️  Skipping malformed line {i+1}")

    results       = [None] * len(items)
    correct = partial = wrong = parse_failures = total_score = 0
    combined_correct = combined_partial = combined_wrong = 0
    combined_total_score = 0.0

    with ThreadPoolExecutor(max_workers=PHASE3_WORKERS) as pool:
        futures = {pool.submit(_judge_one, item): item[0] for item in items}
        for future in as_completed(futures, timeout=PHASE3_TIMEOUT):
            try:
                idx, data = future.result(timeout=PHASE3_TIMEOUT)
            except Exception as e:
                idx = futures[future]
                logger.error(f"  💥 Q{idx+1} crashed: {e}")
                parse_failures += 1
                continue
            results[idx] = data
            if data is not None:
                score = data.get("score", 0)
                combined_score = data.get("combined_score", 0.0)
                combined_judgement = data.get("combined_judgement", 0)
                total_score += score
                combined_total_score += combined_score

                if score == 2:
                    correct += 1
                    status = "✅ CORRECT"
                elif score == 1:
                    partial += 1
                    status = "⚠️  PARTIAL"
                else:
                    wrong += 1
                    status = "❌ WRONG"

                if combined_judgement == 2:
                    combined_correct += 1
                    combined_status = "✅ CORRECT"
                elif combined_judgement == 1:
                    combined_partial += 1
                    combined_status = "⚠️  PARTIAL"
                else:
                    combined_wrong += 1
                    combined_status = "❌ WRONG"

                logger.info(
                    f"Q{idx+1}: {status} | {data.get('reason','')[:80]} "
                    f"| combined {combined_status} ({combined_score:.2f})"
                )
            else:
                parse_failures += 1
                logger.warning(f"  ⚠️  Q{idx+1}: judge returned nothing")

    with open(final_report, "w", encoding="utf-8") as fout:
        for data in results:
            if data is not None:
                fout.write(json.dumps(data, ensure_ascii=False) + "\n")

    total            = correct + partial + wrong
    weighted_score   = (total_score / (total * 2) * 100) if total > 0 else 0
    strict_score     = (correct / total * 100)            if total > 0 else 0

    combined_total = combined_correct + combined_partial + combined_wrong
    combined_weighted_score = (combined_total_score / combined_total * 100) if combined_total > 0 else 0
    combined_strict_score = (combined_correct / combined_total * 100) if combined_total > 0 else 0

    logger.info("\n" + "=" * 40)
    logger.info("📊 FINAL EVALUATION REPORT")
    logger.info("-- Judge-only metrics --")
    logger.info(f"  Total graded:            {total}")
    logger.info(f"  ✅ Correct  (2):         {correct}")
    logger.info(f"  ⚠️  Partial  (1):         {partial}   (+{partial} pts)")
    logger.info(f"  ❌ Wrong      (0):         {wrong}")
    logger.info(f"  🎯 Weighted score:       {weighted_score:.1f}%  (correct×2 + partial×1)")
    logger.info(f"  📌 Strict score:         {strict_score:.1f}%   (correct only)")
    logger.info("-- Faithfulness-adjusted metrics --")
    logger.info(f"  Total graded:            {combined_total}")
    logger.info(f"  ✅ Correct  (2):         {combined_correct}")
    logger.info(f"  ⚠️  Partial  (1):         {combined_partial}   (+{combined_partial} pts)")
    logger.info(f"  ❌ Wrong      (0):         {combined_wrong}")
    logger.info(f"  🎯 Combined score:        {combined_weighted_score:.1f}%  (judge+faithfulness)")
    logger.info(f"  📌 Combined strict score: {combined_strict_score:.1f}%")
    logger.info(f"  ⏱️  Phase 3 time:         {time.time()-t0:.1f}s")
    if parse_failures:
        logger.warning(f"  ⚡ Judge errors:         {parse_failures}")
    logger.info("=" * 40)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Generate evaluation results using RAG inference and judging"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        choices=["test", "train", "valid"],
        default="test",
        help="Which evaluation dataset to use (default: test)"
    )
    configure_logging()

    parser.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Randomly sample N questions (default: 5 questions; set 0 for all questions)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for more verbose status output"
    )
    args = parser.parse_args()

    if args.debug:
        configure_logging(logging.DEBUG)
        logger.debug("Debug logging enabled")

    DATA_FILE    = get_data_file(args.dataset)
    RAG_ANSWERS  = os.path.join(EVAL_DIR, f"rag_responses_{args.dataset}.jsonl")
    FINAL_REPORT = os.path.join(EVAL_DIR, f"final_evaluation_{args.dataset}.jsonl")
    os.makedirs(EVAL_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        logger.error(f"❌ Dataset file not found: {DATA_FILE}")
        logger.error(f"   Make sure you've run merge_eval_datasets.py first to create the split datasets.")
        exit(1)

    logger.info(f"📁 Dataset file: {DATA_FILE}")
    logger.info(f"🐘 Process ID: {os.getpid()}")
    logger.info("⏱️  Counting questions in dataset file...")
    q_count = sum(1 for l in open(DATA_FILE, encoding="utf-8") if l.strip())
    logger.info(f"📋 Loaded {q_count} questions from '{DATA_FILE}' (dataset: {args.dataset})")

    brain = Brain()
    logger.info(f"🧠 Brain indices present? {brain.is_built()}")
    if brain.is_built():
        logger.info("✅ Existing indices detected; loading brain directly.")
        brain.load()
    else:
        logger.info("🔄 Syncing indices...")
        brain.sync_indices()

    logger.info("🚀 Starting Phase 2 (RAG inference). This may take a while, especially on the first question.")
    run_rag_inference(brain, args, DATA_FILE, RAG_ANSWERS)
    logger.info("🚀 Starting Phase 3 (Judge & report).")
    run_judge_and_report(RAG_ANSWERS, FINAL_REPORT)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )
    main()
