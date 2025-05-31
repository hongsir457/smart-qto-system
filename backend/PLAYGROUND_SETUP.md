# AI Playground 功能设置指南

## 概述
AI Playground 功能已成功集成到智能工程量计算系统中，提供了类似 OpenAI Playground 的交互式 AI 对话体验。

## 功能特性

### 1. 核心功能
- **多模型支持**: 支持 GPT-4o、GPT-4、GPT-3.5-turbo 等模型
- **参数调节**: 可调节温度、最大令牌数、Top P、频率惩罚、存在惩罚等参数
- **预设模板**: 内置多种专业场景的预设模板
- **对话管理**: 支持对话历史记录、清空、导出功能
- **实时验证**: API 密钥状态实时验证
- **流式响应**: 支持流式对话（实验性功能）

### 2. 预设模板
- **智能助手**: 通用AI助手，适用于各种问题
- **工程量计算专家**: 专门用于建筑图纸分析和工程量计算
- **代码生成器**: 专业的代码生成和解释
- **创意写作助手**: 用于创意写作和内容生成

## 配置要求

### 1. 环境变量配置
在 `backend/.env` 文件中添加以下配置：

```env
# OpenAI API配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
```

### 2. 依赖安装
确保安装了以下 Python 包：
```bash
pip install openai>=1.0.0
```

### 3. API 端点
Playground 功能提供以下 API 端点：
- `POST /api/v1/playground/chat` - 发送聊天消息
- `GET /api/v1/playground/models` - 获取可用模型列表
- `GET /api/v1/playground/presets` - 获取预设模板
- `POST /api/v1/playground/validate` - 验证 API 密钥
- `GET /api/v1/playground/usage` - 获取使用统计
- `POST /api/v1/playground/stream` - 流式聊天

## 使用方法

### 1. 访问 Playground
- 登录系统后，点击导航栏中的 "AI Playground" 按钮
- 或直接访问 `/playground` 路径

### 2. 基本使用
1. 选择预设模板（可选）
2. 调整模型参数（可选）
3. 在输入框中输入消息
4. 按 Enter 发送消息或点击发送按钮
5. 查看 AI 回复

### 3. 高级功能
- **参数调节**: 点击"显示设置"按钮调整模型参数
- **导出对话**: 点击"导出对话"按钮保存对话记录
- **清空对话**: 点击"清空对话"按钮重新开始

## 故障排除

### 1. API 密钥问题
如果显示 "API状态: 异常"，请检查：
- OpenAI API 密钥是否正确配置
- API 密钥是否有效且未过期
- 是否有足够的 API 配额

### 2. 模型访问问题
如果无法访问 GPT-4o：
- 确认您的 OpenAI 账户有 GPT-4o 的 API 访问权限
- 尝试使用其他可用模型（如 GPT-3.5-turbo）
- 检查 API 密钥的权限设置

### 3. 网络连接问题
- 确保服务器可以访问 OpenAI API
- 检查防火墙设置
- 验证网络连接稳定性

## 安全注意事项

1. **API 密钥保护**: 
   - 不要在前端代码中暴露 API 密钥
   - 使用环境变量存储敏感信息
   - 定期轮换 API 密钥

2. **用户权限控制**:
   - 确保只有授权用户可以访问 Playground
   - 实施适当的使用限制和监控

3. **数据隐私**:
   - 注意不要发送敏感或机密信息
   - 了解 OpenAI 的数据使用政策

## 扩展功能

### 1. 自定义预设
可以在 `backend/api/v1/endpoints/playground.py` 中的 `PRESET_TEMPLATES` 数组中添加自定义预设模板。

### 2. 使用统计
系统提供基本的使用统计功能，可以根据需要集成更详细的监控和分析。

### 3. 流式响应
实验性的流式响应功能已实现，可以提供更好的用户体验。

## 技术架构

### 后端
- **FastAPI**: 提供 RESTful API
- **OpenAI Python SDK**: 与 OpenAI API 交互
- **Pydantic**: 数据验证和序列化
- **异步处理**: 支持异步 API 调用

### 前端
- **React + TypeScript**: 现代化的前端框架
- **Ant Design**: 美观的 UI 组件库
- **Axios**: HTTP 客户端
- **响应式设计**: 适配不同屏幕尺寸

## 更新日志

### v1.0.0 (当前版本)
- ✅ 基础聊天功能
- ✅ 多模型支持
- ✅ 参数调节
- ✅ 预设模板
- ✅ 对话管理
- ✅ API 密钥验证
- ✅ 导航集成
- ✅ 响应式设计

### 计划功能
- 🔄 对话历史持久化
- 🔄 更多预设模板
- 🔄 批量处理功能
- 🔄 API 使用统计详情
- 🔄 多语言支持 