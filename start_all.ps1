# Smart QTO System - Startup Script
Write-Host "===========================================" -ForegroundColor Green
Write-Host "      Smart QTO System Startup" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Check virtual environment
if (!(Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "1. Checking environment..." -ForegroundColor Yellow

# Check Redis
Write-Host "2. Checking Redis status..." -ForegroundColor Yellow
$redisProcess = Get-Process redis-server -ErrorAction SilentlyContinue
if ($redisProcess) {
    Write-Host "✓ Redis is running" -ForegroundColor Green
} else {
    Write-Host "Warning: Redis is not running" -ForegroundColor Yellow
    Write-Host "Tip: Run redis-server or double-click start_redis.bat" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "3. Starting services..." -ForegroundColor Yellow

# Stop existing Python processes
Write-Host "Stopping existing Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host ""

# Start Celery Worker
Write-Host "Starting Celery Worker..." -ForegroundColor Cyan
$celeryCommand = "cd '$PWD'; & .\venv\Scripts\Activate.ps1; cd backend; python celery_worker.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $celeryCommand

Start-Sleep -Seconds 3

# Start FastAPI Server
Write-Host "Starting FastAPI Server..." -ForegroundColor Cyan
$apiCommand = "cd '$PWD'; & .\venv\Scripts\Activate.ps1; cd backend; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $apiCommand

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "Startup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Please check the new windows:" -ForegroundColor White
Write-Host "• Celery Worker window" -ForegroundColor White
Write-Host "• FastAPI Server window" -ForegroundColor White
Write-Host ""
Write-Host "Access URLs:" -ForegroundColor Yellow
Write-Host "• API Service: http://localhost:8000" -ForegroundColor White
Write-Host "• API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "• Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "===========================================" -ForegroundColor Green

pause 