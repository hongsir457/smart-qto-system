# Smart QTO System - Celery Worker 启动脚本
# 解决Windows下Ctrl+C无法停止的问题

Write-Host "🚀 Smart QTO System - Celery Worker 启动器" -ForegroundColor Green
Write-Host "=" * 50

# 检查并停止现有的Celery进程
Write-Host "🔍 检查现有的Python/Celery进程..." -ForegroundColor Yellow
$existingProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue

if ($existingProcesses) {
    Write-Host "⚠️  发现 $($existingProcesses.Count) 个现有Python进程" -ForegroundColor Yellow
    Write-Host "🛑 停止现有进程..." -ForegroundColor Red
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "✅ 已停止现有进程" -ForegroundColor Green
} else {
    Write-Host "✅ 没有发现现有进程" -ForegroundColor Green
}

# 设置环境变量
$env:PYTHONPATH = (Get-Location).Path
Write-Host "📁 工作目录: $(Get-Location)" -ForegroundColor Cyan
Write-Host "🐍 Python路径: $env:PYTHONPATH" -ForegroundColor Cyan

# 启动Celery Worker
Write-Host ""
Write-Host "🎯 启动Celery Worker..." -ForegroundColor Green
Write-Host "💡 提示: 使用 Ctrl+Break 或关闭窗口来停止worker" -ForegroundColor Yellow
Write-Host "💡 或者运行 Stop-Process -Name 'python' -Force 来强制停止" -ForegroundColor Yellow
Write-Host ""

try {
    # 使用start-process来启动，这样更容易管理
    celery -A celery_worker worker --loglevel=info --pool=solo --concurrency=1
} catch {
    Write-Host "❌ Celery启动失败: $_" -ForegroundColor Red
    pause
} finally {
    Write-Host ""
    Write-Host "🛑 Celery Worker已停止" -ForegroundColor Red
    Write-Host "按任意键退出..."
    pause
} 