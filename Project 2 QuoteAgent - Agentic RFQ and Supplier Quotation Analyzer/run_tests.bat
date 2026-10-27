@echo off
echo ========================================================
echo QuoteAgent - Run All Unit Tests
echo ========================================================
cd /d "%~dp0"
set PYTHONPATH=%~dp0
python -m pytest tests -v
pause
