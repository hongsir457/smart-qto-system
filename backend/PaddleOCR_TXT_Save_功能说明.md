# PaddleOCR TXT格式保存功能说明

## 功能概述

本功能扩展了PaddleOCR服务，现在可以同时将识别结果保存为JSON和TXT两种格式到Sealos云存储，提供更好的人类可读性和数据访问便利性。

## 主要特性

### 1. 双格式保存
- **JSON格式**: 机器可读的完整数据结构，包含原始坐标、置信度等技术信息
- **TXT格式**: 人类可读的格式化文本，便于查看和分析

### 2. 详细的TXT内容结构
```
============================================================
PaddleOCR识别结果
============================================================
图像文件: construction_drawing.png
识别时间: 2024-01-15 10:30:00

检测到 5 个文本区域:

[01] 文本: KZ-1 400x400
     置信度: 0.970
     位置: (100, 50) - (200, 80)
     尺寸: 100 x 30

[02] 文本: C30
     置信度: 0.920
     位置: (100, 100) - (180, 130)
     尺寸: 80 x 30

----------------------------------------
统计信息:
平均置信度: 0.945
最高置信度: 0.970
最低置信度: 0.920
总字符数: 52
总文本数: 5

----------------------------------------
纯文本内容:
----------------------------------------
KZ-1 400x400
C30
Construction Drawing
KL-1 300x600
HRB400
```

### 3. 智能排序和组织
- **详细信息**: 按置信度从高到低排序
- **纯文本区域**: 按图像位置从上到下、从左到右排序
- **统计摘要**: 提供识别质量指标

## 技术实现

### 1. S3服务扩展
在 `app/services/s3_service.py` 中添加了：
- `upload_txt_content()`: TXT内容上传方法
- `_upload_txt_to_local()`: 本地TXT保存
- `_upload_txt_to_s3()`: 云端TXT保存

### 2. PaddleOCR服务增强
在 `app/services/ocr/paddle_ocr.py` 中添加了：
- `_format_raw_result_as_txt()`: 将原始识别结果格式化为TXT
- 修改 `_save_complete_raw_result_to_sealos()`: 同时保存JSON和TXT格式

### 3. 存储结构
```
sealos-bucket/
├── ocr_results/
│   ├── raw/                 # JSON格式原始数据
│   │   └── ocr_raw_image_001_abc123.json
│   └── txt/                 # TXT格式人类可读数据
│       └── ocr_raw_image_001_def456.txt
```

## 使用方法

### 基本用法
```python
from app.services.ocr.paddle_ocr import PaddleOCRService

# 创建OCR服务
ocr_service = PaddleOCRService()

# 执行识别并保存（默认启用TXT保存）
result = ocr_service.recognize_text(
    image_path="construction_drawing.png",
    save_to_sealos=True
)

# 检查保存结果
storage_info = result.get('storage_info', {})
if storage_info.get('saved'):
    # JSON文件信息
    json_info = storage_info.get('json_result', {})
    print(f"JSON文件: {json_info.get('s3_key')}")
    
    # TXT文件信息
    txt_info = storage_info.get('txt_result', {})
    print(f"TXT文件: {txt_info.get('s3_key')}")
    print(f"文件大小: {txt_info.get('file_size')} bytes")
```

### 返回数据结构
```python
{
    "storage_info": {
        "saved": True,
        "json_result": {
            "s3_key": "ocr_results/raw/ocr_raw_drawing_abc123.json",
            "s3_url": "https://...",
            "bucket": "your-bucket"
        },
        "txt_result": {
            "s3_key": "ocr_results/txt/ocr_raw_drawing_def456.txt",
            "s3_url": "https://...",
            "bucket": "your-bucket",
            "filename": "ocr_raw_drawing_def456.txt",
            "file_size": 1024
        },
        "error": None
    }
}
```

## 配置选项

### 存储设置
在 `app/core/config.py` 中配置：
```python
# S3存储配置
S3_ENDPOINT = "https://objectstorageapi.hzh.sealos.run"
S3_BUCKET = "your-bucket-name"
S3_ACCESS_KEY = "your-access-key"
S3_SECRET_KEY = "your-secret-key"
```

### TXT格式定制
可以通过修改 `_format_raw_result_as_txt()` 方法来自定义TXT输出格式：
- 调整排序规则
- 修改显示内容
- 增加或减少统计信息

## 测试验证

运行测试脚本验证功能：
```bash
# 简单功能测试
python simple_txt_test.py

# 完整的OCR+自动resize+TXT保存测试
python test_auto_resize_ocr.py
```

## 优势和应用场景

### 1. 建筑工程应用
- 快速查看图纸识别结果
- 构件信息人工核对
- 工程量数据验证

### 2. 数据处理优势
- **JSON**: 程序化处理和分析
- **TXT**: 人工审查和验证
- **统一存储**: 便于数据管理

### 3. 工作流优化
- 一次识别，双格式输出
- 自动云端存储
- 便于团队协作查看

## 注意事项

1. **文件大小**: TXT文件通常比JSON文件小，但包含的技术信息较少
2. **编码**: 使用UTF-8编码确保中文支持
3. **存储成本**: 双格式保存会增加一定的存储空间
4. **访问权限**: 确保Sealos存储桶配置正确的访问权限

## 错误处理

如果TXT保存失败，系统会：
1. 记录详细错误日志
2. 返回错误信息在 `storage_info.error` 中
3. 不影响JSON格式的正常保存
4. 提供graceful fallback机制

## 版本兼容性

- 向后兼容：现有的JSON保存功能不受影响
- 可选功能：可以通过修改代码禁用TXT保存
- 渐进式增强：在原有功能基础上扩展

---

**更新时间**: 2024-01-15  
**版本**: v1.0  
**维护者**: Smart QTO System Team 