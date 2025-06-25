# Celery Worker启动指南 (Windows环境)

## 🔧 启动命令对比

### 🎯 推荐配置 (Windows)

#### 1. 开发环境 - 使用solo池
```bash
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

#### 2. 生产环境 - 使用threads池  
```bash
celery -A app.core.celery_app worker --loglevel=info --pool=threads --concurrency=4
```

#### 3. 调试模式 - 详细日志
```bash
celery -A app.core.celery_app worker --loglevel=debug --pool=solo --concurrency=1
```

---

## 📊 池类型对比

| 池类型 | 适用场景 | 优点 | 缺点 | Windows兼容性 |
|--------|----------|------|------|---------------|
| **solo** | 开发/调试 | 稳定、简单、易调试 | 单线程、性能低 | ✅ 完美支持 |
| **threads** | 生产环境 | 多线程、性能好 | 线程安全要求 | ✅ 良好支持 |
| **prefork** | Unix生产 | 进程隔离、高性能 | 内存占用高 | ❌ Windows不支持 |
| **gevent** | 高并发IO | 协程、高并发 | 异步编程复杂 | ⚠️ 需额外配置 |

---

## 🚀 启动步骤

### 第1步: 启动Redis服务
```bash
# 检查Redis是否运行
redis-cli ping

# 如果没有响应，启动Redis
redis-server
```

### 第2步: 选择合适的Celery启动命令

#### 🎯 推荐: 开发环境使用solo池
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

**为什么推荐solo池？**
- ✅ **Windows兼容性最佳**: 避免进程/线程相关问题
- ✅ **调试友好**: 单线程执行，错误定位容易
- ✅ **稳定性高**: 不会出现并发冲突
- ✅ **开发阶段足够**: OCR任务处理时间5-15秒可接受

#### 🔥 性能需求: 生产环境使用threads池
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info --pool=threads --concurrency=4
```

**适用场景:**
- ✅ **高并发需求**: 需要同时处理多个任务
- ✅ **生产环境**: 用户访问量大的情况
- ⚠️ **需要更多内存**: 多线程会增加内存消耗

---

## 🧪 测试验证

### 验证Worker是否正常启动
```bash
# 检查Worker状态
celery -A app.core.celery_app inspect stats

# 检查注册的任务
celery -A app.core.celery_app inspect registered

# 检查活跃任务
celery -A app.core.celery_app inspect active
```

### 运行测试任务
```bash
# 运行Celery配置诊断
python test_celery_tasks.py

# 运行异步工作流测试
python test_async_workflow.py
```

---

## 🔍 常见问题和解决方案

### 问题1: 无法启动Worker
```bash
# 错误: ImportError或模块找不到
# 解决: 确认在正确目录下启动
cd backend
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

### 问题2: Redis连接失败
```bash
# 错误: kombu.exceptions.OperationalError
# 解决: 启动Redis服务
redis-server

# 检查Redis配置
redis-cli ping
```

### 问题3: 任务执行失败
```bash
# 错误: Task卡住或失败
# 解决: 使用solo池调试
celery -A app.core.celery_app worker --loglevel=debug --pool=solo
```

### 问题4: 并发问题 (Windows特有)
```bash
# 错误: Windows上进程/线程错误
# 解决: 强制使用solo池
celery -A app.core.celery_app worker --pool=solo --concurrency=1
```

---

## ⚙️ 高级配置

### 自定义并发数
```bash
# solo池 (固定并发=1)
celery -A app.core.celery_app worker --pool=solo

# threads池 (自定义并发)
celery -A app.core.celery_app worker --pool=threads --concurrency=2

# 根据CPU核心数自动设置
celery -A app.core.celery_app worker --pool=threads --autoscale=8,2
```

### 内存和任务限制
```bash
# 限制每个Worker最大任务数
celery -A app.core.celery_app worker --pool=solo --max-tasks-per-child=100

# 设置内存限制 (MB)
celery -A app.core.celery_app worker --pool=solo --max-memory-per-child=500000
```

### 队列和路由
```bash
# 指定处理特定队列
celery -A app.core.celery_app worker --pool=solo --queues=default,ocr_queue

# 设置预取数量
celery -A app.core.celery_app worker --pool=solo --prefetch-multiplier=1
```

---

## 📋 生产环境部署建议

### Windows Server部署
```bash
# 使用Windows Service方式运行
# 1. 安装pywin32
pip install pywin32

# 2. 创建Windows服务
python -m celery -A app.core.celery_app worker --pool=threads --concurrency=4 --detach

# 3. 或使用nssm工具创建服务
nssm install CeleryWorker "C:\Python\python.exe"
nssm set CeleryWorker Parameters "-m celery -A app.core.celery_app worker --pool=threads"
```

### 监控和日志
```bash
# 输出到日志文件
celery -A app.core.celery_app worker --pool=solo --logfile=logs/celery.log

# 设置日志级别
celery -A app.core.celery_app worker --pool=solo --loglevel=warning

# 启用事件监控
celery -A app.core.celery_app worker --pool=solo --events
```

---

## 🎯 最终推荐

### 👑 开发环境 (强烈推荐)
```bash
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

### 🚀 生产环境
```bash
celery -A app.core.celery_app worker --loglevel=warning --pool=threads --concurrency=4
```

### 🔧 调试模式
```bash
celery -A app.core.celery_app worker --loglevel=debug --pool=solo --concurrency=1
```

---

## 💡 性能提示

1. **Windows环境建议使用`--pool=solo`** - 最稳定的选择
2. **生产环境可尝试`--pool=threads`** - 更好的并发性能
3. **避免使用`prefork`池** - Windows不支持
4. **调试时始终使用`solo`池** - 错误更容易定位
5. **监控内存使用** - 设置合理的任务限制

---

🎉 **总结**: 对于Windows环境，建议优先使用 `--pool=solo` 参数以确保最佳稳定性！ 