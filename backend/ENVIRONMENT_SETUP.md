# 环境配置说明

## 必需配置

### 1. 创建 .env 文件
在 `backend/` 目录下创建 `.env` 文件，包含以下配置：

```env
# OpenAI API配置 (必需)
OPENAI_API_KEY=sk-your-openai-api-key-here

# JWT配置
SECRET_KEY=your-secret-key-here-change-this-in-production

# 数据库配置
DATABASE_URL=sqlite:///./app/database.db

# 应用配置
PROJECT_NAME=Smart QTO System
VERSION=1.0.0
API_V1_STR=/api/v1
```

### 2. 获取 OpenAI API 密钥

1. 访问 [OpenAI API Keys](https://platform.openai.com/api-keys)
2. 登录您的 OpenAI 账户
3. 点击 "Create new secret key"
4. 复制生成的密钥（格式：sk-...）
5. 将密钥粘贴到 `.env` 文件中的 `OPENAI_API_KEY` 字段

### 3. 验证配置

启动后端服务后，访问 AI Playground 页面：
- 如果 API 状态显示 "正常"，说明配置成功
- 如果显示 "异常"，请检查 API 密钥是否正确

## 可选配置

```env
# Redis配置 (用于缓存)
REDIS_URL=redis://localhost:6379

# PostgreSQL配置 (替代SQLite)
POSTGRES_URL=postgresql://user:password@localhost:5432/smartqto

# 文件上传配置
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=50MB

# 调试模式
DEBUG=True

# Tesseract OCR配置
TESSERACT_CMD=tesseract
```

## 故障排除

### API 密钥问题
- 确保密钥以 `sk-` 开头
- 检查密钥是否有效且未过期
- 确认账户有足够的 API 配额

### 权限问题
- 确保有 GPT-3.5-turbo 的访问权限
- 如需使用 GPT-4，确认账户已升级

### 网络问题
- 确保服务器可以访问 api.openai.com
- 检查防火墙设置 