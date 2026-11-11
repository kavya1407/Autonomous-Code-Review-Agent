Write-Host "Starting Autonomous Code Review & Refactoring Agent..." -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
