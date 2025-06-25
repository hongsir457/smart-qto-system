# 智能工程量计算系统 - 8000端口启动脚本
Write-Host "🚀 启动智能工程量计算系统 (端口8000)" -ForegroundColor Green

# 1. 停止所有可能的Python进程
Write-Host "🛑 清理现有进程..." -ForegroundColor Yellow
try {
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} catch {
    Write-Host "无需清理进程" -ForegroundColor Gray
}

# 2. 检查8000端口是否被占用
Write-Host "🔍 检查8000端口状态..." -ForegroundColor Yellow
$portCheck = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "⚠️ 8000端口被占用，尝试释放..." -ForegroundColor Red
    $process = Get-Process -Id $portCheck.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $process.Id -Force
        Start-Sleep -Seconds 3
    }
}

# 3. 确认端口已释放
$portCheck2 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $portCheck2) {
    Write-Host "✅ 8000端口已释放" -ForegroundColor Green
} else {
    Write-Host "❌ 8000端口仍被占用，请手动检查" -ForegroundColor Red
    exit 1
}

# 4. 启动FastAPI服务器
Write-Host "🌟 在8000端口启动FastAPI服务器..." -ForegroundColor Cyan
try {
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} catch {
    Write-Host "❌ 启动失败: $_" -ForegroundColor Red
    exit 1
} 