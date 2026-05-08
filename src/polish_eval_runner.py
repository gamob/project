import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.eval.polish_eval_runner import main

if __name__ == "__main__":
    main()
