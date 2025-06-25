# Windows下Celery Worker使用说明

## 问题说明

在Windows系统中，Celery Worker经常出现 `Ctrl+C` 无法正常关闭的问题，这是由于：

1. Windows PowerShell信号处理机制与Linux不同
2. Celery在Windows上的信号响应存在问题  
3. PaddleOCR等长时间初始化任务会阻塞进程关闭
4. 多进程模式在Windows下不稳定

## 解决方案

### 1. 推荐启动方式

```powershell
# 方式一：使用启动脚本（推荐）
.\start_celery.ps1

# 方式二：直接命令
python celery_worker.py
```

### 2. 停止方式

```powershell
# 方式一：使用停止脚本（推荐）
.\stop_celery.ps1

# 方式二：在worker终端窗口中
# 尝试 Ctrl+Break（不是Ctrl+C）

# 方式三：强制停止（备用方案）
Stop-Process -Name "python" -Force
```

### 3. 配置优化

新的worker配置包含以下Windows特定优化：

- `--pool=solo`: 使用单进程模式，避免多进程问题
- `--concurrency=1`: 单进程并发
- `--without-heartbeat`: 禁用心跳机制（Windows下不稳定）
- `--without-gossip`: 禁用gossip协议
- `--without-mingle`: 禁用mingle协议

### 4. 信号处理改进

- 增加了 `SIGBREAK` 信号处理（Ctrl+Break）
- 实现优雅关闭机制，等待当前任务完成
- 添加监控线程，确保进程能正常退出
- 支持多种关闭信号（SIGINT, SIGTERM, SIGBREAK）

## 故障排除

### 如果worker仍然无法关闭：

1. **关闭终端窗口**：直接关闭PowerShell窗口
2. **任务管理器**：打开任务管理器，结束python.exe进程
3. **PowerShell强制停止**：
   ```powershell
   Get-Process -Name "python" | Stop-Process -Force
   ```

### 如果遇到端口占用：

```powershell
# 检查端口占用
netstat -an | Select-String ":5672|:6379|:8000"

# 找到占用进程并结束
netstat -ano | Select-String ":端口号"
Stop-Process -Id <PID> -Force
```

## 最佳实践

1. **使用专用脚本**：总是使用 `start_celery.ps1` 和 `stop_celery.ps1`
2. **定期重启**：长时间运行后定期重启worker以释放内存
3. **监控资源**：注意PaddleOCR初始化时的内存使用
4. **任务限制**：使用 `--max-tasks-per-child=10` 限制任务数，防止内存泄露

## 常见错误及解决

- **"cannot import name"错误**：检查PYTHONPATH设置
- **Redis连接失败**：确保Redis服务正在运行
- **PaddleOCR初始化卡住**：等待60秒超时，或重启worker
- **内存不足**：降低并发数或重启worker 