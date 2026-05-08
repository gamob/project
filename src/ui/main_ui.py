"""
main_ui.py — Interactive UI for running evaluation pipeline scripts.

Navigate and execute different pipeline stages with warnings and prerequisites checking.

Usage:
    python main_ui.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from rich.console import Console

console = Console()


class ScriptRunner:
    """Manage script execution with prerequisites and feedback."""
    
    def __init__(self):
        self.src_dir = Path(__file__).parent
        self.project_root = self.src_dir.parent
        
    def check_file_exists(self, file_path):
        """Check if a file exists."""
        full_path = self.project_root / file_path
        return full_path.exists()
    
    def get_file_size(self, file_path):
        """Get human-readable file size."""
        full_path = self.project_root / file_path
        if not full_path.exists():
            return "N/A"
        size = full_path.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def count_jsonl_lines(self, file_path):
        """Count lines in JSONL file."""
        full_path = self.project_root / file_path
        if not full_path.exists():
            return 0
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def run_script(self, script_name, description, prerequisites=None, output_files=None):
        """Run a script with prerequisites checking."""
        console.print("\n" + "="*70)
        console.print(f"📜 SCRIPT: {script_name}")
        console.print("="*70)
        console.print(f"📝 {description}\n")
        
        # Check prerequisites
        if prerequisites:
            console.print("📋 Prerequisites:")
            all_met = True
            for prereq_file, prereq_desc in prerequisites:
                exists = self.check_file_exists(prereq_file)
                status = "✅" if exists else "❌"
                size = self.get_file_size(prereq_file)
                console.print(f"  {status} {prereq_desc}")
                console.print(f"     Path: {prereq_file} ({size})")
                if not exists:
                    all_met = False
            
            if not all_met:
                console.print("\n⚠️  MISSING FILES!")
                response = input("Continue anyway? (y/n): ").strip().lower()
                if response != 'y':
                    console.print("❌ Cancelled.")
                    return
        
        # Show output files
        if output_files:
            console.print("\n📁 Expected outputs:")
            for output_file, output_desc in output_files:
                exists = self.check_file_exists(output_file)
                status = "✅" if exists else "⏳"
                console.print(f"  {status} {output_desc}: {output_file}")
        
        # Confirmation
        console.print("\n" + "-"*70)
        response = input("Run this script now? (y/n): ").strip().lower()
        if response != 'y':
            console.print("❌ Cancelled.")
            return
        
        # Execute
        console.print("\n" + "="*70)
        console.print("🚀 RUNNING SCRIPT...")
        console.print("="*70 + "\n")
        
        script_path = self.src_dir / script_name
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                console.print("\n" + "="*70)
                console.print("✅ SCRIPT COMPLETED SUCCESSFULLY")
                console.print("="*70)
            else:
                console.print("\n" + "="*70)
                console.print(f"⚠️  SCRIPT EXITED WITH CODE {result.returncode}")
                console.print("="*70)
        
        except Exception as e:
            console.print(f"\n❌ ERROR RUNNING SCRIPT: {e}")


def display_menu():
    """Display main menu and get user choice."""
    console.print("\n" + "="*70)
    console.print("🧠 RAG EVALUATION PIPELINE")
    console.print("="*70)
    console.print("\nChoose what to run:\n")
    console.print("  [1] Generate Raw Questions")
    console.print("     └─ Create 200 raw questions from your knowledge base")
    console.print("     └─ Output: evaluation/eval_dataset.jsonl\n")
    
    console.print("  [2] Merge Datasets")
    console.print("     └─ Combine 200 generated + 80 custom questions")
    console.print("     └─ Split into train/valid/test (60/20/20)")
    console.print("     └─ Output: eval_train.jsonl, eval_valid.jsonl, eval_test.jsonl\n")
    
    console.print("  [3] Generate Evaluations")
    console.print("     └─ Run RAG evaluation on test questions")
    console.print("     └─ Generate responses and calculate metrics\n")
    
    console.print("  [4] View Statistics")
    console.print("     └─ Show dataset statistics and file info\n")
    
    console.print("  [0] Exit\n")
    
    return input("Enter choice (0-4): ").strip()


def show_statistics(runner):
    """Display dataset statistics."""
    console.print("\n" + "="*70)
    console.print("📊 DATASET STATISTICS")
    console.print("="*70 + "\n")
    
    files_to_check = [
        ("evaluation/eval_dataset.jsonl", "Generated Questions"),
        ("evaluation/eval_custom_questions.jsonl", "Custom Questions"),
        ("evaluation/eval_train.jsonl", "Train Split"),
        ("evaluation/eval_valid.jsonl", "Validation Split"),
        ("evaluation/eval_test.jsonl", "Test Split"),
    ]
    
    for file_path, desc in files_to_check:
        exists = runner.check_file_exists(file_path)
        if exists:
            count = runner.count_jsonl_lines(file_path)
            size = runner.get_file_size(file_path)
            console.print(f"✅ {desc}")
            console.print(f"   File: {file_path}")
            console.print(f"   Size: {size} | Entries: {count}\n")
        else:
            console.print(f"❌ {desc}")
            console.print(f"   File: {file_path} (NOT FOUND)\n")


def main():
    """Main UI loop."""
    runner = ScriptRunner()
    
    console.print("\n" + "█"*70)
    console.print("█" + " "*68 + "█")
    console.print("█" + "  🤖 RAG EVALUATION PIPELINE MANAGER".center(68) + "█")
    console.print("█" + " "*68 + "█")
    console.print("█"*70)
    
    while True:
        choice = display_menu()
        
        if choice == '1':
            # Generate Raw Questions
            runner.run_script(
                "prep_questions.py",
                "Generate 200 raw evaluation questions from your knowledge base.",
                prerequisites=[
                    ("data/", "Knowledge base data"),
                    ("model/bge-m3/", "Embedding model"),
                ],
                output_files=[
                    ("evaluation/eval_dataset.jsonl", "Generated raw questions"),
                ]
            )
        
        elif choice == '2':
            # Merge Datasets
            runner.run_script(
                "merge_eval_datasets.py",
                "Merge 200 generated questions + 80 custom questions and split into train/valid/test.",
                prerequisites=[
                    ("evaluation/eval_dataset.jsonl", "Generated questions (200)"),
                    ("evaluation/eval_custom_questions.jsonl", "Custom hard questions (80)"),
                ],
                output_files=[
                    ("evaluation/eval_train.jsonl", "Training set (168 questions)"),
                    ("evaluation/eval_valid.jsonl", "Validation set (56 questions)"),
                    ("evaluation/eval_test.jsonl", "Test set (56 questions)"),
                ]
            )
        
        elif choice == '3':
            # Generate Evaluations
            runner.run_script(
                "generate_evals.py",
                "Run RAG evaluation on test questions and generate responses.",
                prerequisites=[
                    ("evaluation/eval_test.jsonl", "Test questions"),
                    ("model/Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf", "LLM model"),
                    ("model/bge-reranker-v2-m3/", "Reranking model"),
                ],
                output_files=[
                    ("evaluation/eval_results.jsonl", "Evaluation results with scores"),
                ]
            )
        
        elif choice == '4':
            # Statistics
            show_statistics(runner)
        
        elif choice == '0':
            console.print("\n👋 Goodbye!\n")
            break
        
        else:
            console.print("\n❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n👋 Interrupted. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
