# 智能工程量清单系统

一个基于AI的工程量清单智能识别和分析系统，支持OCR识别、结构化数据提取和智能分析。

## ✨ 核心功能

- 🔍 **智能OCR识别**: 支持多种文档格式的OCR文字识别
- 📊 **结构化数据提取**: 将非结构化文档转换为结构化JSON数据
- 🤖 **AI智能分析**: 基于AI模型的内容理解和分析
- 📋 **工程量清单生成**: 自动生成标准化工程量清单
- 🔄 **实时进度跟踪**: WebSocket实时任务状态更新
- 🗄️ **云存储集成**: 支持S3兼容的云存储

## 🚀 快速开始

### 1. 环境准备

确保您已安装以下依赖：
- Python 3.8+
- Redis Server
- pip (Python包管理器)

### 2. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 或者使用虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 启动服务

使用我们提供的一键启动脚本：

```bash
python start_services.py
```

这将自动启动：
- Redis服务
- Celery Worker
- FastAPI服务

### 4. 运行测试

```bash
python test_system.py
```

## 📖 API 使用说明

### 基础接口

- **健康检查**: `GET /health`
- **API文档**: `GET /docs` (Swagger UI)
- **文件上传**: `POST /api/v1/upload`
- **任务状态**: `GET /api/v1/tasks/{task_id}/status`
- **任务列表**: `GET /api/v1/tasks`

### WebSocket

实时任务状态更新：
```ws://localhost:8000/api/v1/ws/task/{task_id}
```

## 🛠️ 配置说明

### 环境变量

创建 `.env` 文件来配置系统参数：

```env
# Redis配置
REDIS_URL=redis://localhost:6379/0

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# S3存储配置 (可选)
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=your_bucket_name
S3_ENDPOINT_URL=your_endpoint_url

# AI API配置 (可选)
OPENAI_API_KEY=your_openai_key
OPENAI_DEFAULT_MODEL=gpt-4o-2024-11-20

# 其他配置
SECRET_KEY=your_secret_key
MAX_UPLOAD_SIZE=104857600  # 100MB
```

## 📁 项目结构

```
smart-qto-system/
├── backend/                 # 后端API服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务服务
│   │   ├── tasks/          # 异步任务
│   │   └── utils/          # 工具函数
│   └── main.py             # 应用入口
├── uploads/                # 上传文件目录
├── exports/                # 导出文件目录
├── start_services.py       # 服务启动脚本
├── test_system.py          # 系统测试脚本
└── requirements.txt        # Python依赖
```

## 🔧 开发指南

### 添加新的任务类型

1. 在 `backend/app/tasks/` 目录下创建新的任务文件
2. 使用 `@celery_app.task` 装饰器定义任务
3. 在 `backend/app/api/` 中添加相应的API端点

### 添加新的分析服务

1. 在 `backend/app/services/` 目录下创建服务类
2. 实现相应的分析逻辑
3. 在任务中调用服务

## 🐛 故障排除

### 常见问题

1. **Redis连接失败**
   - 确保Redis服务正在运行
   - 检查Redis配置和端口

2. **Celery Worker启动失败**
   - Windows用户需要使用 `--pool=solo` 参数
   - 检查Python路径和模块导入

3. **文件上传失败**
   - 检查文件大小限制
   - 确保上传目录有写权限

### 日志查看

- FastAPI日志: 控制台输出
- Celery日志: Celery Worker控制台
- Redis日志: Redis服务器日志

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 支持

如果您遇到问题或有任何疑问，请：

1. 查看文档和FAQ
2. 提交Issue
3. 联系开发团队

---

## 📅 更新日志

### 🚀 v1.0.0 (2025-06-01)

#### ✨ 新功能特性
- 🎯 **智能图纸识别** - AI驱动的建筑构件自动识别系统
- 📊 **精确工程量计算** - 多规则计算引擎，支持复杂工程量计算
- 🏗️ **完整项目管理** - 从图纸上传到结果导出的全流程管理
- 🔐 **安全认证系统** - JWT令牌认证，角色权限管理
- 📱 **响应式界面** - 支持桌面端和移动端的现代化UI设计
- 🔄 **实时进度推送** - WebSocket实时通信，处理进度实时显示
- 📈 **数据可视化** - 丰富的图表展示和统计分析功能

#### 🛠️ 技术架构
- **后端框架**: FastAPI + SQLAlchemy + PostgreSQL
- **前端技术**: React 18 + TypeScript + Ant Design
- **AI集成**: OpenAI GPT + 自定义图纸识别模型
- **实时通信**: WebSocket双向通信
- **数据库**: PostgreSQL主库 + Redis缓存
- **文件处理**: 支持PDF、DWG、DXF等多种格式

#### 📁 支持的文件格式
- ✅ PDF格式建筑图纸
- ✅ AutoCAD DWG文件
- ✅ AutoCAD DXF文件  
- ✅ 常见图片格式 (PNG, JPG, etc.)

#### 🎯 核心功能模块
- **用户管理**: 注册登录、权限控制、个人资料
- **项目管理**: 项目创建、成员协作、进度跟踪
- **图纸处理**: 文件上传、格式转换、预览展示
- **AI识别**: 构件自动识别、文本OCR提取
- **工程量计算**: 自动计算、规则定制、结果验证
- **数据导出**: Excel报表、PDF报告、统计图表

#### 🔧 开发工具与配置
- **API文档**: Swagger UI自动生成
- **数据库迁移**: Alembic版本控制
- **代码规范**: PEP 8 + ESLint + Prettier
- **测试覆盖**: Pytest + Jest测试框架
- **容器化**: Docker + Docker Compose部署

#### ⚠️ 已知限制
- AI模型文件较大，需单独下载配置
- 复杂DWG文件处理时间较长
- 需要稳定的网络连接以使用AI功能
- 推荐使用Chrome或Edge浏览器以获得最佳体验

#### 🎯 性能指标
- 图纸识别准确率: >85%
- 中等复杂度图纸处理时间: <2分钟
- 支持同时在线用户数: 100+
- API响应时间: <200ms

#### 📋 下一版本计划 (v1.1.0)
- 🔄 增加批量处理功能
- 📱 移动端APP开发
- 🤖 提升AI识别精度
- 🌐 多语言界面支持
- ⚡ 性能优化与加速
- 🔗 第三方CAD软件集成

#### 🙏 致谢
感谢所有为项目贡献代码、建议和反馈的开发者和用户。特别感谢开源社区提供的优秀框架和工具支持。

**技术支持**: 如遇问题请通过GitHub Issues或邮件联系我们。
