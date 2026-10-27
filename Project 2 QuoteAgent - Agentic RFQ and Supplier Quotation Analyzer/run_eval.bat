@echo off
echo ========================================================
echo Running QuoteAgent Evaluation Benchmark & Timed Test
echo ========================================================
cd /d "%~dp0"
set PYTHONPATH=%~dp0
python evaluate.py
pause
