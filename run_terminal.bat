@echo off
REM Terminal-based Corporate Brain Launcher
REM Run the terminal app instead of the web version

cd /d "%~dp0"

echo Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

echo Installing/updating Rich library...
python -m pip install -q rich

echo.
echo Starting Corporate Brain (Terminal Mode)...
echo.

cd src
python app_terminal.py

pause
