@echo off
echo ========================================================
echo Launching QuoteAgent Streamlit Web Application
echo ========================================================
cd /d "%~dp0"
set PYTHONPATH=%~dp0
python -m streamlit run app.py
pause
