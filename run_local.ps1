# ==============================================================================
# Smart Classroom Environmental Monitoring System
# Local Windows Server Startup Script
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Smart Classroom Environmental Monitoring System " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check if virtual environment exists
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[1/3] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# 2. Check dependencies
Write-Host "[2/3] Checking dependencies..." -ForegroundColor Yellow
.\.venv\Scripts\pip.exe install -r requirements.txt --quiet

# 3. Start FastAPI Server
Write-Host "[3/3] Starting FastAPI Server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "Interactive API Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "Press Ctrl+C to terminate the server.`n" -ForegroundColor Gray

.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
