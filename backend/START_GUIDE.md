# 🚀 智能工程量计算系统启动指南

## 问题诊断 ✅

**发现的核心问题**: 文件上传后没有派发OCR任务，导致任务一直处于pending状态。

**解决方案**: 
1. ✅ 修复了图纸上传API，添加了OCR任务派发逻辑
2. ✅ 增强了日志记录，便于问题追踪
3. ✅ 添加了任务状态查询端点

## 系统启动步骤

### 1. 启动Redis服务 🔴
```bash
# 检查Redis是否运行
redis-cli ping

# 如果没有响应，启动Redis
redis-server
```

### 2. 启动Celery Worker 🔧
```bash
# 在backend目录下
cd backend

# 启动Worker（Windows环境必须使用--pool=solo）
celery -A app.core.celery_app worker --loglevel=info --pool=solo
```

**重要**: 必须看到以下日志表示Worker启动成功:
```
[INFO/MainProcess] Connected to redis://localhost:6379/0
[INFO/MainProcess] mingle: searching for available workers
[INFO/MainProcess] mingle: all workers reply
[INFO/MainProcess] celery@YOUR-PC ready.
```

### 3. 启动FastAPI服务 🌐
**新开一个终端窗口**:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 验证系统运行 ✅
在backend目录运行测试脚本:
```bash
python test_complete_workflow.py
```

## 测试API功能

### 上传文件测试
```bash
# 使用curl测试文件上传
curl -X POST "http://localhost:8000/api/v1/drawings/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_image.png"
```

### 查询任务状态
```bash
# 查询特定图纸的处理状态
curl -X GET "http://localhost:8000/api/v1/drawings/1/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 日志监控 📊

### 查看实时日志
1. **Celery Worker日志**: 在Worker终端查看任务处理日志
2. **FastAPI日志**: 在FastAPI终端查看API请求日志
3. **Redis监控**: 
   ```bash
   redis-cli monitor
   ```

### 关键日志检查点
- [ ] 文件上传成功
- [ ] OCR任务派发成功
- [ ] Worker接收并处理任务
- [ ] 任务状态更新

## 常见问题排查 🔍

### 问题1: 任务卡在pending状态
**原因**: Celery Worker未启动
**解决**: 按步骤2启动Worker

### 问题2: Worker连接失败
**原因**: Redis未启动
**解决**: 按步骤1启动Redis

### 问题3: 任务执行失败
**检查**: 
1. 文件路径是否存在
2. 权限是否足够
3. 临时目录是否创建

### 问题4: API返回500错误
**检查**:
1. 数据库连接
2. 文件上传目录权限
3. S3配置（如果使用）

## 性能监控 📈

### 查看Worker状态
```bash
# 检查活跃任务
celery -A app.core.celery_app inspect active

# 检查注册的任务
celery -A app.core.celery_app inspect registered

# 查看Worker统计
celery -A app.core.celery_app inspect stats
```

### 队列监控
```bash
# 查看Redis队列长度
redis-cli llen celery

# 查看所有key
redis-cli keys "*"
```

## 生产环境建议 🏭

### 1. 服务器配置
- **Redis**: 使用Redis集群
- **Celery**: 配置多个Worker进程
- **FastAPI**: 使用Gunicorn部署

### 2. 监控配置
- 使用Flower监控Celery
- 配置日志轮转
- 设置告警机制

### 3. 安全配置
- 配置JWT密钥
- 限制文件上传大小
- 设置API访问频率限制

## 开发调试 🔧

### 开发模式启动
```bash
# 终端1: Redis
redis-server

# 终端2: Celery Worker
cd backend
celery -A app.core.celery_app worker --loglevel=debug --pool=solo

# 终端3: FastAPI
cd backend  
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# 终端4: 测试
cd backend
python test_complete_workflow.py
```

## 成功标志 🎉

当看到以下输出时，表示系统运行正常:
```
🎉 所有测试通过!
✅ OCR工作流正常
✅ API模拟正常
🚀 系统可以正常使用!
```

---
**更新时间**: 2024年最新版本  
**技术栈**: FastAPI + Celery + Redis + GPT-4o  
**状态**: ✅ 已修复核心问题，系统可正常使用 