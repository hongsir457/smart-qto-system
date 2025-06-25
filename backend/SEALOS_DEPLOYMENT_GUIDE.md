# Sealos 智能工程量计算系统部署指南

## 🚀 系统概览

本系统已完全集成Sealos云平台，使用以下Sealos服务：
- **PostgreSQL数据库**: 存储用户数据、图纸信息、分析结果
- **S3对象存储**: 存储图纸文件、OCR结果、导出文件
- **Redis缓存**: 任务队列和实时通信

## 📋 系统架构

```
前端(React) → FastAPI后端 → Sealos PostgreSQL
      ↓              ↓
   WebSocket     Sealos S3存储
      ↓              ↓
   Redis队列    Celery任务处理
```

## 🔧 配置步骤

### 1. 复制配置文件

```bash
cp sealos_config.env .env
```

### 2. 修改Sealos配置

编辑 `.env` 文件，更新以下配置：

```bash
# === Sealos S3 对象存储配置 ===
S3_ENDPOINT=https://objectstorageapi.hzh.sealos.run
S3_ACCESS_KEY=你的实际Access_Key
S3_SECRET_KEY=你的实际Secret_Key
S3_BUCKET=你的存储桶名称
S3_REGION=us-east-1

# === AI 配置 ===
OPENAI_API_KEY=你的实际OpenAI_API_Key

# === JWT 配置 ===
SECRET_KEY=生成一个安全的密钥
```

### 3. 获取Sealos S3配置

在Sealos控制台获取S3存储配置：

1. 登录 [Sealos控制台](https://cloud.sealos.io/)
2. 进入 **对象存储** 服务
3. 创建或选择存储桶
4. 在存储桶设置中获取：
   - Access Key
   - Secret Key
   - Endpoint URL
   - 存储桶名称

### 4. 数据库连接

系统已预配置Sealos PostgreSQL连接：
```postgresql://postgres:2xn59xgm@dbconn.sealoshzh.site:48982/postgres
```

如需使用其他数据库，请修改 `DATABASE_URL` 配置。

## 🧪 连接测试

运行测试脚本验证配置：

```bash
cd backend
python test_sealos_connection.py
```

测试项目包括：
- ✅ Sealos PostgreSQL数据库连接
- ✅ Sealos S3对象存储连接  
- ✅ S3Service类功能测试

## 🏗️ 部署运行

### 本地开发环境

1. **启动Redis** (如果本地没有Redis)
```bash
# Windows (使用Docker)
docker run -d -p 6379:6379 redis:alpine

# 或使用WSL安装Redis
```

2. **启动后端系统**
```bash
cd backend
python start_system.py
```

3. **启动前端**
```bash
cd frontend
npm run dev
```

### Sealos云平台部署

1. **后端部署**
   - 创建Sealos应用
   - 上传后端代码
   - 配置环境变量
   - 启动服务

2. **前端部署**
   - 使用Sealos静态网站托管
   - 构建React应用
   - 配置API地址

## 📊 系统监控

### 状态检查

```bash
# 检查系统状态
python system_status_check.py

# 生成状态报告
python system_status_report.py
```

### 日志监控

主要日志位置：
- **应用日志**: FastAPI应用日志
- **Celery日志**: 任务处理日志
- **S3操作日志**: 文件上传下载日志

## 🔒 安全配置

### 1. 环境变量安全

确保 `.env` 文件不被提交到版本控制：
```bash
# .gitignore
.env
sealos_config.env
```

### 2. JWT密钥

生成安全的JWT密钥：
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. S3权限

确保S3存储桶权限设置正确：
- 仅允许授权应用访问
- 启用HTTPS传输
- 配置合理的过期策略

## 🛠️ 故障排除

### 常见问题

1. **S3连接失败**
   ```
   ❌ Sealos S3上传失败: ...
   ```
   解决方案：
   - 检查Access Key和Secret Key
   - 验证存储桶名称
   - 确认网络连接

2. **数据库连接超时**
   ```
   ❌ 数据库连接失败: timeout
   ```
   解决方案：
   - 检查数据库服务状态
   - 验证连接字符串
   - 确认防火墙设置

3. **任务处理失败**
   ```
   ❌ Celery任务执行失败
   ```
   解决方案：
   - 检查Redis连接
   - 重启Celery Worker
   - 查看任务日志

### 调试命令

```bash
# 测试数据库连接
python -c "from app.core.database import engine; print(engine.url)"

# 测试S3连接
python test_sealos_connection.py

# 检查Celery状态
celery -A app.core.celery_app inspect active

# 查看Redis连接
redis-cli ping
```

## 📈 性能优化

### 1. S3优化

- 使用CDN加速文件访问
- 启用S3传输加速
- 配置适当的缓存策略

### 2. 数据库优化

- 创建适当的索引
- 定期清理过期数据
- 使用连接池

### 3. 任务队列优化

- 调整Celery并发数
- 使用任务优先级
- 配置任务重试策略

## 🔄 备份策略

### 1. 数据库备份

```bash
# 自动备份脚本
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### 2. S3文件备份

- 启用S3版本控制
- 配置跨区域复制
- 定期备份重要文件

## 📞 技术支持

如遇到问题，请：

1. 查看系统日志
2. 运行连接测试
3. 检查配置文件
4. 参考故障排除指南

---

## 📋 配置清单

部署前确认：

- [ ] 已获取Sealos S3配置信息
- [ ] 已配置 `.env` 文件
- [ ] 已测试数据库连接
- [ ] 已测试S3存储连接
- [ ] 已安装所有依赖
- [ ] 已配置Redis服务
- [ ] 已生成安全的JWT密钥
- [ ] 已设置合适的CORS配置

完成以上配置后，系统即可正常运行！🎉 