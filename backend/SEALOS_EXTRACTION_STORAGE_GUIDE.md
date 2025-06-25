# Sealos一阶段识别结果存储功能指南

## 📋 功能概述

系统已成功集成Sealos云存储，自动保存一阶段构件识别结果，方便调试阶段的查阅核对。

## 🎯 主要特性

### ✅ 自动保存功能
- **触发时机**: 每次AI构件提取完成后自动保存
- **存储位置**: Sealos S3存储桶 `extraction_results/` 目录
- **文件格式**: JSON格式，包含完整识别元数据

### 📄 文件命名规范
```
stage1_extraction_YYYYMMDD_HHMMSS_<uuid>.json
```
示例: `stage1_extraction_20250610_165137_2d7672d7-66b4-4a9b-be97-080e2188a3ff.json`

### 📊 保存内容结构
```json
{
  "meta": {
    "extraction_id": "唯一识别ID",
    "extraction_time": "识别时间",
    "stage": "一阶段构件识别",
    "system_version": "v1.0",
    "ai_model": "gpt-4o-2024-11-20",
    "source_image": "源图片路径"
  },
  "statistics": {
    "total_components": "构件总数",
    "source_texts": "源文本数量",
    "extraction_method": "AI大模型提取",
    "success": "是否成功"
  },
  "components": [
    {
      "component_id": "构件编号",
      "component_type": "构件类型",
      "name": "构件名称",
      "dimensions": "尺寸信息",
      "material": "材料信息",
      "reinforcement": "配筋信息",
      "confidence": "置信度",
      "source": "来源"
    }
  ],
  "debug_info": {
    "image_path": "图片路径",
    "extraction_status": "提取状态"
  }
}
```

## 🔧 技术实现

### 核心组件
- **AIComponentExtractor**: 集成Sealos存储功能
- **S3Service**: 统一的Sealos S3存储服务
- **自动保存**: 在识别完成后自动触发

### 关键代码位置
```
backend/app/services/ai_component_extractor.py
- _save_extraction_result_to_sealos()  # 保存方法
- extract_components_from_texts()      # 主提取方法

backend/app/services/s3_service.py
- S3Service类                        # S3存储服务
```

## 📈 使用示例

### 1. 运行构件识别
```python
from app.services.ai_component_extractor import AIComponentExtractor

extractor = AIComponentExtractor()
result = extractor.extract_components_from_texts(ocr_texts, image_path)

# 检查Sealos存储状态
sealos_info = result.get("sealos_storage", {})
if sealos_info.get("saved"):
    print(f"✅ 结果已保存到Sealos: {sealos_info['s3_key']}")
    print(f"🔗 访问URL: {sealos_info['s3_url']}")
else:
    print(f"❌ 保存失败: {sealos_info.get('error')}")
```

### 2. 调试工具使用
```bash
# 启动调试工具
python debug_sealos_extraction_results.py

# 或运行演示脚本
python demo_sealos_debug.py
```

### 3. 测试存储功能
```bash
# 测试存储连接
python test_sealos_storage.py

# 测试完整流程
python test_ai_component_extractor.py
```

## 🌐 Sealos配置

### 环境变量配置
```bash
# Sealos S3存储配置
S3_ENDPOINT=https://objectstorageapi.hzh.sealos.run
S3_ACCESS_KEY=你的访问密钥
S3_SECRET_KEY=你的私钥
S3_BUCKET=你的存储桶名称
S3_REGION=us-east-1
```

### 权限要求
- ✅ 上传权限: 保存识别结果
- ⚠️ 下载权限: 查看历史结果（部分限制）
- 📂 目录权限: `extraction_results/` 目录访问

## 🔍 调试和查看

### 自动保存验证
每次识别后，检查返回结果中的 `sealos_storage` 字段：
```json
{
  "sealos_storage": {
    "saved": true,
    "s3_key": "extraction_results/xxx.json",
    "s3_url": "https://...",
    "filename": "stage1_extraction_xxx.json",
    "save_time": "2025-06-10T16:51:37.315113"
  }
}
```

### 手动查看已知结果
如果知道具体的S3键，可以通过调试工具下载查看：
```bash
python debug_sealos_extraction_results.py
# 选择选项2，输入S3键
```

### 测试记录
最近测试保存的文件：
- `extraction_results/ef144f3f-2b92-4792-bd27-6bcbec9b2d41.json`
- 包含4个构件：KZ1、KL1、Q1、B1
- 使用GPT-4o模型成功提取

## 💡 使用建议

### 开发调试阶段
1. **验证保存**: 每次识别后检查 `sealos_storage.saved` 状态
2. **记录S3键**: 保存重要测试的S3键用于后续查看
3. **定期清理**: 清理测试产生的临时文件

### 生产环境
1. **监控存储**: 定期检查Sealos存储使用情况
2. **备份重要结果**: 对关键识别结果进行本地备份
3. **权限管理**: 确保S3权限配置正确

## 🚀 未来改进

### 计划功能
- [ ] S3文件列表功能，支持浏览历史记录
- [ ] 批量下载和分析工具
- [ ] 识别结果对比功能
- [ ] 自动清理过期文件

### 性能优化
- [ ] 异步上传，避免阻塞识别流程
- [ ] 压缩存储，减少存储空间占用
- [ ] 增量保存，只保存变更部分

## 📞 技术支持

如遇问题请检查：
1. Sealos S3配置是否正确
2. 网络连接是否正常
3. 存储桶权限是否充足
4. 查看应用日志获取详细错误信息

---
**更新时间**: 2025-06-10  
**版本**: v1.0  
**状态**: ✅ 已实现并测试通过 