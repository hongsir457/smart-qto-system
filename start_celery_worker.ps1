# Celery Worker 启动脚本
Write-Host "正在启动 Celery Worker..." -ForegroundColor Green

# 切换到 backend 目录
Set-Location -Path "backend"

# 检查虚拟环境
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    Write-Host "激活虚拟环境..." -ForegroundColor Yellow
    & "..\venv\Scripts\Activate.ps1"
} else {
    Write-Host "警告: 未找到虚拟环境" -ForegroundColor Red
}

# 设置环境变量
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
$env:FORKED_BY_MULTIPROCESSING = "1"

Write-Host "当前目录: $PWD" -ForegroundColor Cyan
Write-Host "启动 Celery Worker..." -ForegroundColor Green

# 测试模块导入
Write-Host "测试模块导入..." -ForegroundColor Yellow
try {
    python -c "from app.core.celery_app import celery_app; print('模块导入成功')"
    Write-Host "模块测试通过!" -ForegroundColor Green
} catch {
    Write-Host "模块导入失败!" -ForegroundColor Red
    exit 1
}

# 启动 Celery Worker
Write-Host "使用正确的模块路径启动 Celery..." -ForegroundColor Green
celery -A app.core.celery_app worker --loglevel=info --pool=solo 