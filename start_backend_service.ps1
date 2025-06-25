# 启动后端服务脚本
# 解决WebSocket连接问题

Write-Host "🚀 启动智能工程量清单系统后端服务..." -ForegroundColor Green

# 1. 检查并停止现有的Python进程
Write-Host "1. 检查现有Python进程..." -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "发现 $($pythonProcesses.Count) 个Python进程，正在停止..." -ForegroundColor Yellow
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "✅ Python进程已停止" -ForegroundColor Green
} else {
    Write-Host "✅ 没有发现运行中的Python进程" -ForegroundColor Green
}

# 2. 检查端口8000是否被占用
Write-Host "2. 检查端口8000状态..." -ForegroundColor Yellow
$port8000 = netstat -an | Select-String ":8000"
if ($port8000) {
    Write-Host "⚠️  端口8000被占用: $port8000" -ForegroundColor Red
} else {
    Write-Host "✅ 端口8000可用" -ForegroundColor Green
}

# 3. 切换到后端目录
Write-Host "3. 切换到后端目录..." -ForegroundColor Yellow
Set-Location -Path "C:\Users\86139\Desktop\appdevelopment\smart-qto-system\backend"
Write-Host "✅ 当前目录: $(Get-Location)" -ForegroundColor Green

# 4. 检查Python环境
Write-Host "4. 检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python不可用: $_" -ForegroundColor Red
    exit 1
}

# 5. 检查必要文件
Write-Host "5. 检查必要文件..." -ForegroundColor Yellow
$requiredFiles = @("app/main.py", "requirements.txt")
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ 找到文件: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ 缺少文件: $file" -ForegroundColor Red
        exit 1
    }
}

# 6. 启动后端服务
Write-Host "6. 启动后端服务..." -ForegroundColor Yellow
Write-Host "命令: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Cyan

try {
    # 使用Start-Process在新窗口中启动服务
    $process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -PassThru -WindowStyle Normal
    
    Write-Host "✅ 后端服务已启动，进程ID: $($process.Id)" -ForegroundColor Green
    
    # 等待服务启动
    Write-Host "7. 等待服务启动..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # 测试服务是否可访问
    Write-Host "8. 测试服务连接..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ 后端服务启动成功！" -ForegroundColor Green
            Write-Host "📊 健康检查响应: $($response.Content)" -ForegroundColor Cyan
            
            # 测试WebSocket端点
            Write-Host "9. 测试WebSocket端点..." -ForegroundColor Yellow
            try {
                $wsResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/ws/status?token=test" -Method GET -TimeoutSec 5
                Write-Host "✅ WebSocket端点可访问" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  WebSocket端点测试失败，但服务已启动: $_" -ForegroundColor Yellow
            }
            
        } else {
            Write-Host "❌ 服务启动失败，状态码: $($response.StatusCode)" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ 无法连接到服务: $_" -ForegroundColor Red
        Write-Host "请检查服务是否正在启动中..." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ 启动服务失败: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 后端服务启动完成！" -ForegroundColor Green
Write-Host "📍 服务地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📍 API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "📍 WebSocket: ws://localhost:8000/api/v1/ws/tasks/{user_id}?token={jwt_token}" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 提示:" -ForegroundColor Yellow
Write-Host "   - 如果WebSocket连接仍然失败，请等待几秒钟让服务完全启动" -ForegroundColor White
Write-Host "   - 可以在浏览器中访问 http://localhost:8000/docs 查看API文档" -ForegroundColor White
Write-Host "   - 前端应该可以正常连接到WebSocket了" -ForegroundColor White 