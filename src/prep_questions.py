import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.eval.prep_questions import main

if __name__ == "__main__":
    main()
