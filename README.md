# 智能工程量计算系统 (Smart QTO System)

一个基于AI的智能工程量计算系统，支持图纸自动识别、量计算和项目管理。

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
- 提交 Issue
- 发送邮件至 support@example.com
- 查看文档: [链接]

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 基础功能实现
- AI图纸识别集成 