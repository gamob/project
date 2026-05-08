import logging
import sys
import json
import traceback
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Raw Evaluation Dataset Handler")
    parser.add_argument("--input", "-i", help="Input JSONL file", 
                        default="evaluation/eval_dataset.jsonl")
    parser.add_argument("--output", "-o", help="Output JSONL file",
                        default="evaluation/eval_dataset_raw.jsonl")
    
    args = parser.parse_args()
    
    logger.debug("[DEBUG-4] 🏃‍♂️ Entering main() function...")
    logger.info("\n" + "="*70)
    logger.info("📊 RAG EVALUATION DATASET HANDLER (Raw Dataset)")
    logger.info("Processing raw dataset with messy questions as-is.")
    logger.info("="*70)

    input_file = args.input
    output_file = args.output
    logger.info(f"\n📂 Input:  {input_file}")
    logger.info(f"📂 Output: {output_file}")

    try:
        logger.debug("[DEBUG-5] 📖 Loading raw dataset...")
        
        if not os.path.exists(input_file):
            logger.error(f"❌ Input file not found: {input_file}")
            sys.exit(1)
        
        # Load raw data
        entries = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️  Skipping malformed line {line_num}: {e}")
                    continue
        
        logger.debug(f"[DEBUG-6] ✅ Loaded {len(entries)} entries from raw dataset")
        
        # Save raw data (no modifications)
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        logger.info("📊 Processing complete!")
        logger.info(f"   Total entries: {len(entries)}")
        logger.info(f"   Output saved to: {output_file}")
        
        if entries:
            logger.info("\n📝 Sample entry (raw - as-is):")
            logger.info(f"   {json.dumps(entries[0], ensure_ascii=False, indent=2)}")

    except Exception as e:
        logger.exception("🚨 PROCESSING ERROR 🚨")
        sys.exit(1)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
    )
    logger.debug("[DEBUG-0] 🏁 Hit __name__ == __main__ block")
    try:
        main()
    except Exception:
        logger.exception("🚨 RUNTIME ERROR IN MAIN 🚨")