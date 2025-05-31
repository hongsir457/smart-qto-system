# AI OCR 配置说明

## 🤖 大模型OCR服务配置指南

Smart QTO系统现在支持使用AI大模型进行图像文字识别，通常比传统OCR效果更好，特别是对于建筑图纸这种复杂文档。

## 支持的AI服务

### 1. OpenAI GPT-4o (推荐)
- **模型**: GPT-4o (最新视觉模型)
- **优势**: 识别准确率最高，理解能力最强
- **成本**: 相对较高，按token计费

### 2. Claude-3 Sonnet
- **模型**: Claude-3 Sonnet
- **优势**: 结构化理解能力强，适合技术文档
- **成本**: 中等，按token计费

### 3. 百度文心一言
- **模型**: 文心一言视觉版
- **优势**: 中文识别效果好，价格相对便宜
- **成本**: 较低，按次计费

### 4. 阿里通义千问
- **模型**: Qwen-VL-Plus
- **优势**: 响应速度快，中文支持好
- **成本**: 较低，按token计费

## 配置方法

### 环境变量配置

在系统环境变量或`.env`文件中设置以下API密钥：

```bash
# OpenAI (推荐)
OPENAI_API_KEY=sk-your-openai-api-key

# Claude
CLAUDE_API_KEY=your-claude-api-key

# 百度文心一言
BAIDU_API_KEY=your-baidu-api-key
BAIDU_SECRET_KEY=your-baidu-secret-key

# 阿里通义千问
QWEN_API_KEY=your-qwen-api-key
```

### Windows环境变量设置
```cmd
# 临时设置（当前会话有效）
set OPENAI_API_KEY=sk-your-api-key

# 永久设置（需要管理员权限）
setx OPENAI_API_KEY "sk-your-api-key" /M
```

### Linux/Mac环境变量设置
```bash
# 临时设置
export OPENAI_API_KEY=sk-your-api-key

# 永久设置（添加到 .bashrc 或 .zshrc）
echo 'export OPENAI_API_KEY=sk-your-api-key' >> ~/.bashrc
source ~/.bashrc
```

## API密钥获取方法

### OpenAI GPT-4o
1. 访问 [OpenAI官网](https://platform.openai.com)
2. 注册/登录账号
3. 在API Keys页面创建新密钥
4. 确保账户有足够余额

### Claude-3
1. 访问 [Anthropic官网](https://console.anthropic.com)
2. 注册/登录账号
3. 在API Keys页面创建密钥
4. 阅读使用条款

### 百度文心一言
1. 访问 [百度智能云](https://cloud.baidu.com)
2. 注册/登录账号
3. 开通文心一言服务
4. 获取API Key和Secret Key

### 阿里通义千问
1. 访问 [阿里云DashScope](https://dashscope.aliyun.com)
2. 注册/登录账号
3. 开通通义千问服务
4. 获取API Key

## 使用方法

### 1. 命令行测试
```bash
# 对比传统OCR和AI OCR
python test_ai_vs_traditional_ocr.py your_image.png

# 只测试传统OCR
python test_real_image_ocr.py your_image.png
```

### 2. 代码中使用
```python
from app.services.drawing import extract_text

# 使用AI OCR（自动选择可用服务）
result = extract_text("image.png", use_ai=True)

# 指定AI服务提供商
result = extract_text("image.png", use_ai=True, ai_provider="openai")

# 传统OCR（默认）
result = extract_text("image.png", use_ai=False)
```

### 3. API接口调用
```python
# 在drawing.py的process_ocr_task中
# 可以修改为使用AI OCR
result = extract_text(local_file, use_ai=True)
```

## 成本估算

以一张典型建筑图纸为例：

| 服务商 | 预估成本 | 处理时间 | 识别准确率 |
|--------|----------|----------|------------|
| OpenAI GPT-4o | ¥0.05-0.15 | 3-8秒 | 95%+ |
| Claude-3 | ¥0.03-0.10 | 3-6秒 | 92%+ |
| 百度文心 | ¥0.01-0.03 | 2-5秒 | 88%+ |
| 通义千问 | ¥0.01-0.05 | 2-4秒 | 90%+ |
| 传统OCR | 免费 | 1-2秒 | 70-80% |

## 配置验证

运行以下命令验证配置：

```bash
python -c "
import os
print('OpenAI:', '✅' if os.getenv('OPENAI_API_KEY') else '❌')
print('Claude:', '✅' if os.getenv('CLAUDE_API_KEY') else '❌')
print('百度:', '✅' if os.getenv('BAIDU_API_KEY') else '❌')
print('通义千问:', '✅' if os.getenv('QWEN_API_KEY') else '❌')
"
```

## 故障排除

### 常见问题

1. **API密钥无效**
   - 检查密钥是否正确复制
   - 确认账户余额充足
   - 验证API权限

2. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置
   - 考虑使用代理

3. **模型调用失败**
   - 检查模型名称是否正确
   - 确认服务可用性
   - 查看错误日志

### 调试方法

```bash
# 查看详细错误信息
python test_ai_vs_traditional_ocr.py your_image.png 2>&1 | tee debug.log

# 检查环境变量
echo $OPENAI_API_KEY  # Linux/Mac
echo %OPENAI_API_KEY%  # Windows
```

## 最佳实践

1. **服务选择策略**
   - 开发测试阶段：使用便宜的服务（百度、通义千问）
   - 生产环境：使用准确率高的服务（OpenAI、Claude）
   - 网络受限：使用传统OCR作为备选

2. **成本控制**
   - 设置API调用频率限制
   - 图像压缩优化
   - 结果缓存策略

3. **性能优化**
   - 图像预处理
   - 批量处理
   - 异步调用

## 安全说明

- API密钥请妥善保管，不要提交到版本控制系统
- 定期轮换API密钥
- 监控API使用量和费用
- 遵守各服务商的使用条款

## 更新日志

- v1.0: 支持OpenAI GPT-4o和Claude-3
- v1.1: 添加百度文心一言支持
- v1.2: 添加阿里通义千问支持
- v1.3: 添加自动降级机制 