#!/usr/bin/env pwsh
<#
优化的Celery启动脚本
包含任务恢复检查和稳定性优化
#>

Write-Host "🚀 启动优化的Celery Worker..." -ForegroundColor Green

# 设置环境变量
$env:PYTHONPATH = "."
$env:CELERY_OPTIMIZATION = "true"

# 检查Redis连接
Write-Host "🔍 检查Redis连接..." -ForegroundColor Yellow
try {
    python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=1); r.ping(); print('✅ Redis连接正常')"
} catch {
    Write-Host "❌ Redis连接失败，请先启动Redis" -ForegroundColor Red
    exit 1
}

# 任务恢复检查
Write-Host "🔄 执行任务恢复检查..." -ForegroundColor Yellow
python -c "
import sys
sys.path.insert(0, '.')
try:
    from app.tasks.task_recovery import task_recovery_manager
    result = task_recovery_manager.handle_unacknowledged_messages()
    print(f'📊 任务恢复结果: {result}')
    
    # 清理过期任务
    cleaned = task_recovery_manager.cleanup_expired_tasks()
    print(f'🧹 清理了 {cleaned} 个过期任务')
except Exception as e:
    print(f'⚠️ 任务恢复检查失败: {e}')
"

# 启动Celery Worker（优化配置）
Write-Host "🔧 启动Celery Worker（优化配置）..." -ForegroundColor Green

celery -A app.core.celery_app worker `
    --loglevel=info `
    --pool=solo `
    --concurrency=1 `
    --prefetch-multiplier=1 `
    --max-tasks-per-child=10 `
    --task-events `
    --without-gossip `
    --without-mingle `
    --without-heartbeat `
    --logfile=celery_worker.log `
    --pidfile=celery_worker.pid

Write-Host "🎉 Celery Worker已启动" -ForegroundColor Green 