# 智能工程量计算系统 (Smart QTO System)

一个基于AI的智能工程量计算系统，支持图纸自动识别、量计算和项目管理。

## 作者信息

**开发者**: hongsir457  
**邮箱**: [oin1914@gmail.com]  
**GitHub**: [hongsir457](https://github.com/hongsir457)

## 功能特性

- 🎯 **智能图纸识别**: 使用AI技术自动识别建筑图纸中的构件
- 📊 **工程量计算**: 自动计算各种建筑构件的工程量
- 📋 **项目管理**: 完整的项目生命周期管理
- 🔐 **用户认证**: 安全的用户登录和权限管理
- 📱 **响应式界面**: 支持多设备访问的现代化UI
- 🔄 **实时更新**: WebSocket实现的实时进度推送
- 📈 **数据分析**: 工程量统计和可视化

## 技术栈

### 后端
- **FastAPI**: 现代化的Python Web框架
- **SQLAlchemy**: ORM数据库操作
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和会话管理
- **OpenAI API**: AI图纸识别
- **WebSocket**: 实时通信

### 前端
- **React**: 用户界面框架
- **TypeScript**: 类型安全的JavaScript
- **Ant Design**: UI组件库
- **Axios**: HTTP客户端
- **React Router**: 路由管理

## 项目结构

```
smart-qto-system/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API路由
│   │   │   └── services/       # 业务逻辑
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模式
│   │   └── services/       # 业务逻辑
│   ├── requirements.txt    # Python依赖
│   └── alembic/           # 数据库迁移
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/         # 页面组件
│   │   ├── services/      # API服务
│   │   └── utils/         # 工具函数
│   ├── package.json       # Node.js依赖
│   └── public/           # 静态资源
└── README.md
```

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Redis 6+

### 后端设置

1. 创建虚拟环境并激活：
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，设置数据库连接等配置
```

4. 运行数据库迁移：
```bash
alembic upgrade head
```

5. 启动后端服务：
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端设置

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm start
```

### 访问应用

- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

## 主要功能

### 1. 用户管理
- 用户注册和登录
- 角色和权限管理
- 用户配置文件

### 2. 项目管理
- 创建和管理工程项目
- 项目成员协作
- 项目进度跟踪

### 3. 图纸处理
- 上传建筑图纸（支持多种格式）
- AI自动识别图纸内容
- 构件标注和编辑

### 4. 工程量计算
- 自动计算各类构件工程量
- 支持自定义计算规则
- 导出计算结果

### 5. 数据分析
- 工程量统计图表
- 成本分析
- 进度报告

## API 文档

启动后端服务后，可通过以下地址访问API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 开发指南

### 代码规范
- 后端遵循PEP 8规范
- 前端使用ESLint和Prettier
- 提交信息遵循Conventional Commits

### 测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

## 部署

### Docker部署
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

### 手动部署
请参考各环境的部署文档。

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持

如有问题或建议，请：
- 提交 Issue: [GitHub Issues](https://github.com/hongsir457/smart-qto-system/issues)
- 发送邮件至: [您的邮箱地址]
- GitHub讨论: [GitHub Discussions](https://github.com/hongsir457/smart-qto-system/discussions)

## 📅 更新日志

### 🚀 v1.0.0 (2025-01-15)

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

---
**发布说明**: 这是智能工程量计算系统的首个正式版本，标志着从概念到产品的重要里程碑。我们将持续改进系统功能，提升用户体验。

**技术支持**: 如遇问题请通过GitHub Issues或邮件联系我们。 