# Smart QTO System - Celery Worker 停止脚本

Write-Host "🛑 Smart QTO System - Celery Worker 停止器" -ForegroundColor Red
Write-Host "=" * 50

# 查找所有Python进程
Write-Host "🔍 查找Python进程..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "发现 $($pythonProcesses.Count) 个Python进程:" -ForegroundColor Yellow
    
    foreach ($process in $pythonProcesses) {
        Write-Host "  - PID: $($process.Id), 内存: $([math]::Round($process.WorkingSet/1MB, 2))MB" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "🛑 正在停止所有Python进程..." -ForegroundColor Red
    
    try {
        Stop-Process -Name "python" -Force
        Start-Sleep -Seconds 2
        
        # 验证是否停止成功
        $remainingProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
        if ($remainingProcesses) {
            Write-Host "⚠️  仍有 $($remainingProcesses.Count) 个进程未停止，尝试强制终止..." -ForegroundColor Yellow
            foreach ($process in $remainingProcesses) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
        
        Write-Host "✅ 所有Python进程已停止" -ForegroundColor Green
        
    } catch {
        Write-Host "❌ 停止进程时出错: $_" -ForegroundColor Red
    }
    
} else {
    Write-Host "✅ 没有发现运行中的Python进程" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔍 检查端口占用情况..."
try {
    $portUsage = netstat -an | Select-String ":5672|:6379|:8000"
    if ($portUsage) {
        Write-Host "当前端口占用情况:" -ForegroundColor Cyan
        $portUsage | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host "✅ 相关端口未被占用" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  无法检查端口占用" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ 停止操作完成" -ForegroundColor Green
Write-Host "按任意键退出..."
pause 