"""
logging_config.py — Configure logging for the entire RAG system.

Usage in main.py:
    from src.config.logging_config import setup_logging
    setup_logging(level=logging.DEBUG)
"""

import logging
import sys


def setup_logging(level=logging.INFO):
    """
    Configure logging for the entire application.
    
    Args:
        level: logging level (DEBUG, INFO, WARNING, ERROR)
    """
    
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers (prevent duplicates)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Optional: Add file handler for debugging
    try:
        file_handler = logging.FileHandler('rag_debug.log')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"Could not create log file: {e}")
    
    return root_logger


if __name__ == '__main__':
    setup_logging(level=logging.DEBUG)
    root = logging.getLogger()
    root.info("Logging is configured!")
