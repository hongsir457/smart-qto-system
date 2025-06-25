# 新OCR架构说明

## 概述

本系统采用全新的OCR处理架构，专门针对建筑图纸识别进行优化。新架构简化了原有的三层OCR体系，专注于PaddleOCR的深度应用，并结合大模型实现两阶段智能分析。

## 架构设计

### 核心组件

```
┌─────────────────────┐
│   文件上传 (API)      │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  整合处理器          │
│ IntegratedProcessor │
└─────────┬───────────┘
          │
┌─────────▼───────────┐    ┌─────────────────┐
│  PNG转换 + OCR      │────│ PaddleOCR引擎   │
│  PaddleOCREngine    │    │ 2048x2048 DPI   │
└─────────┬───────────┘    └─────────────────┘
          │
┌─────────▼───────────┐
│  一阶段分析          │
│  StageOneAnalyzer   │
│  • 构件识别          │
│  • 尺寸提取          │
│  • 图框信息          │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  二阶段分析          │
│  StageTwoAnalyzer   │
│  • 大模型多轮对话     │
│  • 交叉验证          │
│  • 属性完善          │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  S3存储 + 数据库     │
│  • 中间结果存储      │
│  • 最终构件清单      │
└─────────────────────┘
```

### 处理流程

1. **文件转换阶段**
   - 支持PDF、DWG、DXF、JPG、PNG格式
   - 统一转换为PNG格式
   - 最大支持2048×2048 DPI分辨率

2. **OCR识别阶段**
   - 使用PaddleOCR进行文字和符号识别
   - 专门优化中文建筑符号识别
   - 返回结构化的rec_texts结果

3. **一阶段分析**
   - 构件编号识别（KZ、KL、QB等）
   - 尺寸标注提取（400×400、φ16等）
   - 图框信息解析（工程名称、图纸编号等）
   - 专业类型判断（结构、建筑、电气等）

4. **二阶段分析**
   - 结合PNG图纸进行大模型分析
   - 多轮对话验证构件属性
   - 交叉验证尺寸和数量
   - 生成完整构件清单

## 核心功能

### 1. PaddleOCR引擎

```python
from app.services.drawing_processing.paddle_ocr_engine import PaddleOCREngine

engine = PaddleOCREngine()
result = engine.extract_text_from_image("drawing.png")
```

**特性：**
- 专门针对建筑图纸优化
- 支持复杂布局识别
- 中文构件符号高精度识别
- 自动图像预处理和尺寸调整

### 2. 一阶段分析器

```python
from app.services.drawing_processing.stage_one_analyzer import StageOneAnalyzer

analyzer = StageOneAnalyzer()
result = analyzer.analyze(ocr_result)
```

**功能：**
- 构件类型分类（柱、梁、板、墙等）
- 尺寸信息结构化
- 图纸专业识别
- 构件-尺寸关联分析

### 3. 二阶段分析器

```python
from app.services.drawing_processing.stage_two_analyzer import StageTwoAnalyzer, LLMConfig

llm_config = LLMConfig(
    provider="openai",
    model_name="gpt-4-vision-preview",
    max_tokens=4096
)

analyzer = StageTwoAnalyzer(llm_config)
result = analyzer.analyze(stage_one_result, png_path)
```

**功能：**
- GPT-4V多模态分析
- 三轮对话验证
- 构件属性完善
- 质量评估和建议

### 4. 整合处理器

```python
from app.services.drawing_processing.integrated_processor import IntegratedProcessor, ProcessingConfig

config = ProcessingConfig(
    enable_stage_two=True,
    store_intermediate_results=True,
    max_image_size=2048
)

processor = IntegratedProcessor(config)
result = processor.process_drawing("drawing.pdf", "drawing_001", "user_123")
```

## API接口

### 上传图纸

```http
POST /api/v1/drawings/upload
Content-Type: multipart/form-data

{
  "file": <drawing_file>
}
```

**响应：**
```json
{
  "id": 123,
  "filename": "结构施工图.pdf",
  "status": "processing",
  "message": "图纸上传成功，正在处理中..."
}
```

### 查询处理状态

```http
GET /api/v1/drawings/{drawing_id}/status
```

**响应：**
```json
{
  "id": 123,
  "status": "completed",
  "progress": 100,
  "components_count": 25,
  "processing_time": 45.6,
  "stages_completed": [
    "png_conversion",
    "ocr_recognition", 
    "stage_one_analysis",
    "stage_two_analysis"
  ],
  "s3_urls": {
    "png": "https://s3.../drawings/123/processed.png",
    "final_components": "https://s3.../analysis_results/final_components_123.json"
  }
}
```

### 获取构件清单

```http
GET /api/v1/drawings/{drawing_id}/components
```

**响应：**
```json
{
  "drawing_id": 123,
  "components": [
    {
      "component_id": "KZ1",
      "component_type": "frame_column",
      "component_name": "框架柱",
      "section_size": "400×400",
      "material": "C30混凝土",
      "quantity": 4,
      "unit": "根",
      "position": [125, 115],
      "confidence": 0.95,
      "verification_status": "verified"
    }
  ],
  "total_count": 25
}
```

### 导出Excel

```http
GET /api/v1/drawings/{drawing_id}/export/excel
```

返回Excel文件，包含：
- 构件清单工作表
- 统计信息工作表  
- 处理信息工作表

## 配置说明

### 环境变量

```bash
# OpenAI配置（二阶段分析）
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# AWS S3配置
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=your_bucket_name

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 处理器配置

```python
config = ProcessingConfig(
    enable_stage_two=True,           # 启用二阶段分析
    store_intermediate_results=True, # 存储中间结果
    store_final_png=True,           # 存储处理后的PNG
    max_image_size=2048,            # 最大图像尺寸
    llm_config=LLMConfig(
        provider="openai",
        model_name="gpt-4-vision-preview",
        max_tokens=4096,
        temperature=0.1,
        timeout=60
    )
)
```

## 测试

### 运行测试脚本

```bash
cd backend
python test_new_architecture.py
```

测试内容：
1. PaddleOCR引擎测试
2. 一阶段分析器测试
3. 二阶段分析器测试（模拟模式）
4. 整合处理器测试

### 单元测试

```bash
cd backend
python -m pytest tests/test_drawing_processing.py -v
```

## 部署

### Docker部署

```dockerfile
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . /app
WORKDIR /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 依赖安装

```bash
# 基础依赖
pip install fastapi uvicorn sqlalchemy psycopg2-binary

# OCR相关
pip install paddlepaddle paddleocr pillow opencv-python

# AI模型
pip install openai anthropic

# 数据处理
pip install pandas openpyxl numpy

# AWS服务
pip install boto3

# 图像处理
pip install pdf2image python-multipart
```

## 性能优化

### 1. 并发处理
- 使用Celery进行异步任务处理
- 支持多图纸并行处理
- 合理的任务队列管理

### 2. 缓存策略
- OCR结果缓存
- 一阶段分析结果缓存
- S3预签名URL缓存

### 3. 资源管理
- 临时文件自动清理
- 内存使用优化
- GPU资源调度

## 故障处理

### 常见问题

1. **PaddleOCR安装失败**
   ```bash
   pip install paddlepaddle-gpu==2.4.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
   pip install paddleocr==2.6.1.3
   ```

2. **图像转换失败**
   - 检查输入文件格式
   - 确认文件大小限制
   - 验证图像分辨率

3. **大模型API调用失败**
   - 检查API密钥配置
   - 验证网络连接
   - 确认配额限制

4. **S3存储失败**
   - 检查AWS凭证
   - 验证存储桶权限
   - 确认网络连接

### 日志监控

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

## 更新日志

### v2.0.0 (当前版本)
- 🎉 全新OCR架构上线
- ✨ 专用PaddleOCR引擎
- 🚀 两阶段智能分析
- 📊 完整构件清单输出
- 🔧 优化的API接口
- 📁 S3云存储集成

### 后续计划

- [ ] YOLOv8构件检测集成
- [ ] 更多图纸格式支持
- [ ] 批量处理优化
- [ ] 实时处理状态推送
- [ ] 移动端支持

## 联系方式

如有问题或建议，请联系开发团队。 