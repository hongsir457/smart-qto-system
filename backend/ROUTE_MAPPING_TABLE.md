# 🗺️ 智能工程量分析系统 - 完整路由映射表

> **系统版本**: v2.0 (重构后)  
> **生成时间**: 2024年12月12日  
> **路由总数**: 83个HTTP路由 + 4个WebSocket路由  

## 📊 路由统计总览

| 模块类型 | 路由数量 | 状态 | 描述 |
|---------|---------|------|------|
| 🔐 认证模块 | 2 | ✅ | 用户登录注册 |
| 👥 用户管理 | 13 | ✅ | 用户CRUD和状态管理 |
| 📄 图纸管理 | 20 | ✅ | 图纸上传处理和分析 |
| 🧱 构件管理 | 5 | ✅ | 构件识别和管理 |
| 👁️ OCR识别 | 2 | ✅ | 图纸OCR处理 |
| 📋 任务管理 | 8 | ✅ | 异步任务调度 |
| 📤 数据导出 | 6 | ✅ | 多格式数据导出 |
| 🤖 AI分析 | 19 | ✅ | AI分析引擎 |
| ⚡ WebSocket | 8 | ✅ | 实时通信 |
| 🛠️ 调试工具 | 3 | ✅ | 开发调试 |

## 🏗️ 路由架构层级

```
/api/v1/                          # 主API前缀
├── auth/                         # 🔐 认证模块
├── users/                        # 👥 用户管理
├── drawings/                     # 📄 图纸管理
├── components/                   # 🧱 构件管理
├── ocr/                         # 👁️ OCR识别
├── tasks/                       # 📋 任务管理
├── export/                      # 📤 数据导出
├── ai/                          # 🤖 AI分析
├── ws/                          # ⚡ WebSocket服务
└── debug/                       # 🛠️ 调试工具

/ws/                             # 兼容性WebSocket前缀
└── *                            # 旧版WebSocket路由
```

## 📋 详细路由清单

### 🔐 认证模块 (`/api/v1/auth/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/login` | 用户登录 | 公开 |
| POST | `/register` | 用户注册 | 公开 |

### 👥 用户管理 (`/api/v1/users/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/` | 获取用户列表 | 管理员 |
| POST | `/` | 创建新用户 | 管理员 |
| GET | `/me` | 获取当前用户信息 | 用户 |
| PUT | `/me` | 更新当前用户信息 | 用户 |
| GET | `/me/stats` | 获取当前用户统计 | 用户 |
| POST | `/change-password` | 修改密码 | 用户 |
| POST | `/reset-password` | 重置密码 | 公开 |
| GET | `/{user_id}` | 获取指定用户 | 管理员 |
| PUT | `/{user_id}` | 更新指定用户 | 管理员 |
| DELETE | `/{user_id}` | 删除指定用户 | 管理员 |
| POST | `/{user_id}/activate` | 激活用户 | 管理员 |
| POST | `/{user_id}/deactivate` | 停用用户 | 管理员 |
| GET | `/{user_id}/stats` | 获取用户统计 | 管理员 |

### 📄 图纸管理 (`/api/v1/drawings/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/` | 获取图纸列表 | 用户 |
| POST | `/upload` | 上传单个图纸 | 用户 |
| POST | `/batch/upload` | 批量上传图纸 | 用户 |
| DELETE | `/batch` | 批量删除图纸 | 用户 |
| GET | `/tasks/{task_id}` | 获取上传任务状态 | 用户 |
| GET | `/{drawing_id}` | 获取图纸详情 | 用户 |
| DELETE | `/{drawing_id}` | 删除指定图纸 | 用户 |
| GET | `/{drawing_id}/status` | 获取图纸处理状态 | 用户 |
| POST | `/{drawing_id}/process` | 处理图纸 | 用户 |
| POST | `/{drawing_id}/ocr` | 图纸OCR识别 | 用户 |
| GET | `/{drawing_id}/ocr-results` | 获取OCR结果 | 用户 |
| POST | `/{drawing_id}/detect-components` | 构件检测 | 用户 |
| GET | `/{drawing_id}/components` | 获取构件列表 | 用户 |
| GET | `/{drawing_id}/analysis-results` | 获取分析结果 | 用户 |
| GET | `/{drawing_id}/s3-content/{content_type}` | 获取S3内容 | 用户 |
| GET | `/{drawing_id}/export` | 导出图纸数据 | 用户 |
| GET | `/{drawing_id}/export/preview` | 导出预览 | 用户 |
| GET | `/{drawing_id}/export/excel` | 导出Excel | 用户 |
| GET | `/{drawing_id}/export/json` | 导出JSON | 用户 |
| GET | `/{drawing_id}/export/pdf-report` | 导出PDF报告 | 用户 |

### 🧱 构件管理 (`/api/v1/components/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/` | 获取构件列表 | 用户 |
| GET | `/{component_id}` | 获取构件详情 | 用户 |
| POST | `/batch-update` | 批量更新构件 | 用户 |
| GET | `/templates` | 获取构件模板 | 用户 |
| GET | `/statistics` | 获取构件统计 | 用户 |

### 👁️ OCR识别 (`/api/v1/ocr/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/process-drawing` | 处理图纸OCR | 用户 |
| POST | `/process-results` | 处理OCR结果 | 用户 |

### 📋 任务管理 (`/api/v1/tasks/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/tasks` | 获取任务列表 | 用户 |
| POST | `/tasks/ocr` | 创建OCR任务 | 用户 |
| POST | `/tasks/batch-ocr` | 批量OCR任务 | 用户 |
| GET | `/tasks/stats` | 获取任务统计 | 用户 |
| GET | `/tasks/{task_id}/status` | 获取任务状态 | 用户 |
| GET | `/tasks/{task_id}/result` | 获取任务结果 | 用户 |
| GET | `/tasks/{task_id}/history` | 获取任务历史 | 用户 |
| DELETE | `/tasks/{task_id}` | 删除任务 | 用户 |

### 📤 数据导出 (`/api/v1/export/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/excel/{drawing_id}` | 导出Excel | 用户 |
| GET | `/json/{drawing_id}` | 导出JSON | 用户 |
| GET | `/csv/{drawing_id}` | 导出CSV | 用户 |
| GET | `/pdf/{drawing_id}` | 导出PDF | 用户 |
| POST | `/batch/{format}` | 批量导出 | 用户 |
| GET | `/templates` | 获取导出模板 | 用户 |

### 🤖 AI分析模块 (`/api/v1/ai/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/analyze-drawing/{drawing_id}` | 分析图纸 | 用户 |
| POST | `/chat-analysis` | 聊天分析 | 用户 |
| GET | `/model-status` | 获取模型状态 | 用户 |
| GET | `/supported-models` | 支持的模型 | 用户 |
| POST | `/upload-and-analyze` | 上传并分析 | 用户 |
| POST | `/batch-analyze` | 批量分析 | 用户 |
| GET | `/analysis-history/{drawing_id}` | 分析历史 | 用户 |
| DELETE | `/analysis/{drawing_id}` | 删除分析 | 用户 |

#### 🤖 ChatGPT子模块 (`/api/v1/ai/chatgpt/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/analyze-pdf` | PDF分析 | 用户 |
| GET | `/analysis-status/{task_id}` | 分析状态 | 用户 |
| DELETE | `/analysis/{task_id}` | 删除分析 | 用户 |
| GET | `/download-excel/{task_id}` | 下载Excel | 用户 |
| GET | `/supported-models` | 支持模型 | 用户 |

#### 🧪 AI测试场 (`/api/v1/ai/playground/`)

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/chat` | 聊天测试 | 用户 |
| GET | `/models` | 可用模型 | 用户 |
| GET | `/presets` | 预设模板 | 用户 |
| POST | `/stream` | 流式响应 | 用户 |
| GET | `/usage` | 使用统计 | 用户 |
| POST | `/validate` | 验证配置 | 用户 |

### ⚡ WebSocket服务 (`/api/v1/ws/`)

| 协议 | 路径 | 功能 | 权限 |
|------|------|------|------|
| WS | `/task-status/{user_id}` | 任务状态推送 | 用户 |
| WS | `/drawing-progress/{drawing_id}` | 图纸进度推送 | 用户 |
| WS | `/ai-analysis/{session_id}` | AI分析推送 | 用户 |
| WS | `/realtime/{connection_id}` | 实时更新 | 用户 |
| POST | `/status` | 连接状态 | 用户 |
| POST | `/broadcast/{channel}` | 广播消息 | 管理员 |
| POST | `/push/task-update/{user_id}` | 推送任务更新 | 系统 |
| POST | `/push/drawing-progress/{drawing_id}` | 推送图纸进度 | 系统 |

### 🛠️ 调试工具 (`/api/v1/debug/`) 

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 公开 |
| GET | `/calculation-debug/{drawing_id}` | 计算调试 | 开发者 |
| POST | `/test-config` | 测试配置 | 开发者 |

## 🔄 兼容性路由 (`/ws/`)

为了向后兼容，系统保留了旧版WebSocket路由：

| 协议 | 路径 | 功能 | 状态 |
|------|------|------|------|
| WS | `/realtime/{connection_id}` | 实时通信 | 🚧 兼容中 |
| WS | `/drawing-upload/{user_id}` | 图纸上传推送 | 🚧 兼容中 |
| WS | `/analysis-progress/{task_id}` | 分析进度推送 | 🚧 兼容中 |
| WS | `/system-notification/{user_id}` | 系统通知 | 🚧 兼容中 |

## 🔍 中间件和权限验证

### 认证中间件

- **JWT验证**: 所有需要权限的路由都需要JWT token
- **用户隔离**: 用户只能访问自己的数据
- **管理员特权**: 管理员可以访问所有用户数据

### CORS配置

```python
# 当前配置
allow_origins = ["*"]          # 生产环境需要修改
allow_credentials = True
allow_methods = ["*"]
allow_headers = ["*"]
```

### WebSocket认证

- **连接认证**: WebSocket连接需要JWT验证
- **频率限制**: 防止连接滥用
- **自动断开**: 无效连接自动清理

## ⚠️ 已知问题和建议

### 1. 路由冲突问题

**问题**: main.py中同时注册了 `/ws` 和 `/api/v1/ws` 前缀

**建议**:
```python
# 推荐配置 - 统一前缀
# 主要WebSocket服务
app.include_router(api_router, prefix="/api/v1")

# 兼容性支持（可选）
app.include_router(legacy_websocket_router, prefix="/ws")
```

### 2. 安全性建议

- [ ] **CORS配置**: 生产环境需要限制具体域名
- [ ] **API限流**: 添加请求频率限制
- [ ] **输入验证**: 加强参数验证和清理
- [ ] **日志审计**: 记录所有关键操作

### 3. 性能优化建议

- [ ] **缓存策略**: 添加Redis缓存热点数据
- [ ] **数据库优化**: 为高频查询添加索引
- [ ] **文件处理**: 大文件分片上传支持
- [ ] **WebSocket集群**: 支持多实例负载均衡

## 🔧 维护说明

### 添加新路由

1. 在对应的`endpoints/`模块中添加路由
2. 在`api.py`中注册路由
3. 更新本文档
4. 运行路由检查脚本验证

### 路由验证工具

```bash
# 运行路由映射检查
python check_routes.py

# 测试FastAPI启动
python main.py
```

### 文档更新

每次路由变更后，请更新：
- [x] 本路由映射表
- [ ] API文档（Swagger）
- [ ] 前端路由配置
- [ ] 部署配置文件

---

**文档维护者**: 系统架构师  
**最后更新**: 2024年12月12日  
**下次审查**: 2024年12月26日 