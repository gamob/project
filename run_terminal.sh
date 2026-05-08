#!/bin/bash

# Terminal-based Corporate Brain Launcher (Linux/Mac)
# Suppresses Streamlit warnings and starts the app

cd "$(dirname "$0")"

echo "Checking Python environment..."
python3 --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

echo "Installing/updating Rich library..."
python3 -m pip install -q rich 2>/dev/null

echo ""
echo "Starting Corporate Brain (Terminal Mode)..."
echo ""

cd src

# Suppress Streamlit warnings on Linux
export STREAMLIT_LOGGER_LEVEL=error
export PYTHONWARNINGS="ignore::UserWarning"

python3 app_terminal.py
