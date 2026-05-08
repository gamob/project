"""
merge_eval_datasets.py — Merge generated and custom evaluation questions into train/valid/test splits.

Combines:
  - Generated raw questions: evaluation/eval_dataset.jsonl (200 questions)
  - Custom hard questions: evaluation/eval_custom_questions.jsonl (80 questions)
  Total: 280 questions

Splits: 60% train / 20% valid / 20% test (168 / 56 / 56)

Usage:
    python merge_eval_datasets.py              # default paths
    python merge_eval_datasets.py --generated path/to/generated.jsonl --custom path/to/custom.jsonl
"""

import json
import argparse
import logging
import random
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_jsonl(file_path):
    """Load JSONL file and return list of entries."""
    entries = []
    if not os.path.exists(file_path):
        logger.warning(f"⚠️  File not found: {file_path}")
        return entries
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        entry = json.loads(line.strip())
                        entries.append(entry)
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️  Skipping malformed line {line_num} in {file_path}: {e}")
                        continue
        logger.info(f"✅ Loaded {len(entries)} entries from {file_path}")
    except Exception as e:
        logger.error(f"❌ Error loading {file_path}: {e}")
    
    return entries


def save_jsonl(file_path, entries):
    """Save list of entries to JSONL file."""
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    logger.info(f"💾 Saved {len(entries)} entries to {file_path}")


def split_data(entries, train_ratio=0.6, valid_ratio=0.2):
    """
    Split data into train/valid/test sets.
    
    train_ratio: proportion for training (default 0.6)
    valid_ratio: proportion for validation (default 0.2)
    test_ratio: remaining (1 - train_ratio - valid_ratio)
    """
    test_ratio = 1 - train_ratio - valid_ratio
    
    # Shuffle entries
    random.shuffle(entries)
    
    total = len(entries)
    train_size = int(total * train_ratio)
    valid_size = int(total * valid_ratio)
    
    train_data = entries[:train_size]
    valid_data = entries[train_size:train_size + valid_size]
    test_data = entries[train_size + valid_size:]
    
    return train_data, valid_data, test_data


def main():
    parser = argparse.ArgumentParser(
        description="Merge generated and custom evaluation questions into train/valid/test splits"
    )
    parser.add_argument(
        "--generated",
        default="evaluation/eval_dataset.jsonl",
        help="Path to generated questions JSONL file"
    )
    parser.add_argument(
        "--custom",
        default="evaluation/eval_custom_questions.jsonl",
        help="Path to custom questions JSONL file"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.6,
        help="Proportion for training set (default 0.6)"
    )
    parser.add_argument(
        "--valid-ratio",
        type=float,
        default=0.2,
        help="Proportion for validation set (default 0.2)"
    )
    
    args = parser.parse_args()
    
    logger.info("\n" + "="*70)
    logger.info("📊 EVALUATION DATASET MERGER")
    logger.info("="*70)
    
    # Load data
    logger.info("\n📖 Loading datasets...")
    generated = load_jsonl(args.generated)
    custom = load_jsonl(args.custom)
    
    if not generated and not custom:
        logger.error("❌ No data found in either file!")
        return
    
    # Merge
    all_entries = generated + custom
    total = len(all_entries)
    logger.info(f"\n📦 Merged datasets:")
    logger.info(f"   Generated: {len(generated)}")
    logger.info(f"   Custom: {len(custom)}")
    logger.info(f"   Total: {total}")
    
    # Split
    train_ratio = args.train_ratio
    valid_ratio = args.valid_ratio
    test_ratio = 1 - train_ratio - valid_ratio
    
    train_data, valid_data, test_data = split_data(all_entries, train_ratio, valid_ratio)
    
    # Save
    logger.info(f"\n✂️  Splitting (train={train_ratio:.0%} / valid={valid_ratio:.0%} / test={test_ratio:.0%})...")
    output_dir = "evaluation"
    save_jsonl(f"{output_dir}/eval_train.jsonl", train_data)
    save_jsonl(f"{output_dir}/eval_valid.jsonl", valid_data)
    save_jsonl(f"{output_dir}/eval_test.jsonl", test_data)
    
    logger.info(f"\n✅ Processing complete!")
    logger.info(f"   Train: {len(train_data)} entries")
    logger.info(f"   Valid: {len(valid_data)} entries")
    logger.info(f"   Test: {len(test_data)} entries")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )
    main()
