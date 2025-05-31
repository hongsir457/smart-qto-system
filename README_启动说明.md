# 智能QTO系统启动说明

## 🚀 一键启动（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File start_all.ps1
```

## 📋 手动启动步骤

### 1. 准备环境
```powershell
# 激活虚拟环境
.\venv\Scripts\Activate.ps1
```

### 2. 启动Redis（新终端窗口）
```powershell
# 方法1：直接运行
redis-server

# 方法2：使用批处理文件
start_redis.bat
```

### 3. 启动Celery Worker（新终端窗口）
```powershell
# 激活虚拟环境并启动
.\venv\Scripts\Activate.ps1
cd backend
python celery_worker.py

# 或使用批处理文件
start_celery.bat
```

### 4. 启动FastAPI服务器（新终端窗口）
```powershell
# 激活虚拟环境并启动
.\venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用批处理文件
start_api.bat
```

## 🌐 访问地址

启动完成后，可以通过以下地址访问：

- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **前端应用**: http://localhost:3000
- **Redis**: localhost:6379

## 🔧 常用命令

### 检查服务状态
```powershell
# 检查端口占用
netstat -an | findstr :8000
netstat -an | findstr :6379

# 检查Python进程
tasklist | findstr python
```

### 停止所有服务
```powershell
# 停止所有Python进程
taskkill /F /IM python.exe

# 停止Redis
taskkill /F /IM redis-server.exe
```

### 重启服务
```powershell
# 停止所有服务
taskkill /F /IM python.exe

# 重新运行启动脚本
powershell -ExecutionPolicy Bypass -File start_all.ps1
```

## ⚠️ 故障排除

### 1. 虚拟环境问题
如果提示找不到虚拟环境，请确保：
- 虚拟环境已创建：`python -m venv venv`
- 路径正确：`.\venv\Scripts\Activate.ps1`

### 2. Redis连接问题
如果Redis连接失败：
- 确保Redis已安装
- 启动Redis服务：`redis-server`
- 检查端口6379是否被占用

### 3. 端口占用问题
如果端口8000被占用：
```powershell
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程（替换PID）
taskkill /F /PID <PID>
```

### 4. 权限问题
如果PowerShell执行策略限制：
```powershell
# 临时允许执行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 或使用绕过参数
powershell -ExecutionPolicy Bypass -File start_all.ps1
```

## 📁 文件说明

- `start_all.ps1` - 一键启动脚本
- `start_redis.bat` - Redis启动脚本
- `start_celery.bat` - Celery Worker启动脚本
- `start_api.bat` - FastAPI服务器启动脚本

## 🎉 启动成功标志

当看到以下信息时，表示启动成功：
- ✅ 新打开了两个PowerShell窗口
- ✅ Celery Worker窗口显示worker启动信息
- ✅ FastAPI服务器窗口显示"Uvicorn running on..."
- ✅ 可以访问 http://localhost:8000/docs

---

**祝您使用愉快！** 🎊 