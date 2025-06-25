# PowerShell Script to start Celery Worker robustly

# 1. Set working directory to the script's location
Push-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Path -Parent)

Write-Host "当前工作目录: $(Get-Location)" -ForegroundColor Cyan

# 2. Define backend directory
$BackendDir = "backend"
if (-not (Test-Path -Path $BackendDir)) {
    Write-Host "错误: 'backend' 目录未找到。" -ForegroundColor Red
    Pop-Location
    exit 1
}

# 3. Define and activate virtual environment
$VenvPath = "venv\Scripts\Activate.ps1"
if (-not (Test-Path -Path $VenvPath)) {
    Write-Host "警告: 在 '$VenvPath' 未找到虚拟环境。" -ForegroundColor Yellow
} else {
    Write-Host "正在激活虚拟环境..." -ForegroundColor Green
    . $VenvPath
}

# 4. Set Environment Variables for Celery
# Ensure PYTHONPATH includes the backend directory for module resolution
$env:PYTHONPATH = "$(Resolve-Path -Path $BackendDir);$env:PYTHONPATH"
# Required for Celery on Windows
$env:FORKED_BY_MULTIPROCESSING = "1"

Write-Host "PYTHONPATH已设置为: $env:PYTHONPATH" -ForegroundColor Cyan

# 5. Change to backend directory before running celery
Push-Location -Path $BackendDir

Write-Host "切换到目录: $(Get-Location)" -ForegroundColor Cyan

# 6. Start Celery Worker
Write-Host "正在启动Celery Worker..." -ForegroundColor Green
Write-Host "命令: celery -A app.core.celery_app worker --loglevel=info --pool=solo"

# Execute the command
celery -A app.core.celery_app worker --loglevel=info --pool=solo

# 7. Restore original location
Pop-Location
Pop-Location