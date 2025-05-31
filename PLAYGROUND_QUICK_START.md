# AI Playground 快速启动指南

## 🚀 快速开始

### 1. 环境配置

#### 配置 OpenAI API 密钥
在 `backend/.env` 文件中添加：
```env
OPENAI_API_KEY=your-openai-api-key-here
```

#### 安装依赖
```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd ../frontend
npm install
```

### 2. 启动系统

#### 方法一：使用启动脚本（推荐）
```bash
# Windows
start_playground_system.bat

# 或手动启动
```

#### 方法二：手动启动
```bash
# 启动后端
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端（新终端）
cd frontend
npm run dev
```

### 3. 访问系统

- **前端应用**: http://localhost:3000
- **AI Playground**: http://localhost:3000/playground
- **API 文档**: http://localhost:8000/docs

## 🎯 功能概览

### 核心功能
- ✅ **多模型支持**: GPT-4o, GPT-4, GPT-3.5-turbo
- ✅ **参数调节**: 温度、最大长度、Top P 等
- ✅ **预设模板**: 智能助手、工程专家、代码生成器等
- ✅ **对话管理**: 历史记录、清空、导出
- ✅ **实时验证**: API 状态监控

### 预设模板
1. **智能助手** - 通用AI助手
2. **工程量计算专家** - 建筑图纸分析专家
3. **代码生成器** - 专业代码生成
4. **创意写作助手** - 内容创作助手

## 🔧 配置说明

### API 密钥配置
```env
# 必需配置
OPENAI_API_KEY=sk-your-api-key-here

# 可选配置
OPENAI_API_BASE=https://api.openai.com/v1
```

### 模型权限
确保您的 OpenAI 账户有以下模型的访问权限：
- `gpt-4o` (推荐)
- `gpt-4`
- `gpt-3.5-turbo`

## 🎮 使用教程

### 基础使用
1. 登录系统
2. 点击导航栏 "AI Playground"
3. 选择预设模板（可选）
4. 输入消息并发送
5. 查看AI回复

### 高级功能
- **调整参数**: 点击"显示设置"调整模型参数
- **导出对话**: 保存对话记录为JSON文件
- **清空对话**: 重新开始新的对话

## 🔍 故障排除

### 常见问题

#### 1. API状态显示异常
**问题**: 页面显示 "API状态: 异常"
**解决方案**:
- 检查 `OPENAI_API_KEY` 是否正确配置
- 验证API密钥是否有效
- 确认账户有足够的API配额

#### 2. 无法访问GPT-4o
**问题**: 模型列表中没有GPT-4o
**解决方案**:
- 确认OpenAI账户有GPT-4o API访问权限
- 尝试使用GPT-3.5-turbo作为替代
- 联系OpenAI支持获取访问权限

#### 3. 网络连接错误
**问题**: 请求超时或连接失败
**解决方案**:
- 检查网络连接
- 验证防火墙设置
- 确认服务器可以访问api.openai.com

### 日志查看
- **后端日志**: 查看后端终端输出
- **前端日志**: 打开浏览器开发者工具查看Console
- **API文档**: 访问 http://localhost:8000/docs 测试API

## 📋 API 端点

### Playground API
```
POST /api/v1/playground/chat          # 发送聊天消息
GET  /api/v1/playground/models        # 获取模型列表
GET  /api/v1/playground/presets       # 获取预设模板
POST /api/v1/playground/validate      # 验证API密钥
GET  /api/v1/playground/usage         # 获取使用统计
POST /api/v1/playground/stream        # 流式聊天
```

### 请求示例
```javascript
// 发送聊天消息
const response = await fetch('/api/v1/playground/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: '你好' }
    ],
    model: 'gpt-4o',
    temperature: 0.7,
    max_tokens: 1000
  })
});
```

## 🔒 安全注意事项

1. **API密钥安全**
   - 不要在前端代码中暴露API密钥
   - 使用环境变量存储敏感信息
   - 定期轮换API密钥

2. **访问控制**
   - 确保用户认证正常工作
   - 实施适当的使用限制
   - 监控API使用情况

3. **数据隐私**
   - 不要发送敏感或机密信息
   - 了解OpenAI数据使用政策
   - 考虑实施内容过滤

## 🚀 下一步

### 扩展功能
- 添加更多预设模板
- 实现对话历史持久化
- 集成更详细的使用统计
- 支持文件上传和分析

### 自定义配置
- 修改预设模板: `backend/api/v1/endpoints/playground.py`
- 调整UI样式: `frontend/src/components/Playground.tsx`
- 添加新的API端点: `backend/api/v1/endpoints/playground.py`

## 📞 支持

如果遇到问题，请：
1. 查看本文档的故障排除部分
2. 检查系统日志
3. 访问API文档进行测试
4. 联系技术支持

---

**祝您使用愉快！** 🎉 