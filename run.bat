@echo off
echo Starting Autonomous Code Review & Refactoring Agent...
call .\.venv\Scripts\activate.bat
uvicorn main:app --reload --host 0.0.0.0 --port 8000
