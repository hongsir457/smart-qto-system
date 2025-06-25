# 轨道1的PaddleOCR汇总结果经OpenAI清洗后的保存位置详解

## 问题回答

**轨道1的PaddleOCR汇总结果经OpenAI清洗后返回的结果保存在哪里？**

## 数据流程分析

### 1. 轨道1 - OCR轨道处理流程

```
PaddleOCR切片扫描 → OCR结果汇总 → OpenAI清洗分析 → 全图概览结果
```

#### Step 1: PaddleOCR切片扫描
- **位置**: `enhanced_grid_slice_analyzer.py` 的 `_extract_ocr_from_slices()` 方法
- **功能**: 对24个切片分别进行OCR文字识别
- **输出**: 每个切片的原始OCR文本和坐标信息

#### Step 2: OCR结果汇总
- **位置**: `_extract_global_ocr_overview_from_slices()` 方法
- **功能**: 将24个切片的OCR结果合并成一个汇总文本
- **代码**:
```python
# 汇总所有切片的OCR文本
combined_text = ""
for slice_info in self.enhanced_slices:
    if slice_info.ocr_results:
        for ocr_item in slice_info.ocr_results:
            combined_text += f"{ocr_item.text}\n"
```

#### Step 3: OpenAI清洗分析
- **位置**: `_extract_global_ocr_overview_from_slices()` 方法第1224行
- **功能**: 使用GPT-4o分析汇总的OCR文本，提取结构化信息
- **模型**: `gpt-4o-2024-11-20`
- **提示词**: 专业结构工程师角色，提取图纸基本信息和构件清单

## 保存位置详解

### 1. 内存保存 - 类实例变量

**主要保存位置**: `self.global_drawing_overview`

```python
# 在 EnhancedGridSliceAnalyzer 类中
self.global_drawing_overview = global_overview_result["overview"]
```

**数据结构**:
```json
{
  "drawing_info": {
    "drawing_title": "从OCR中识别的图纸标题",
    "drawing_number": "从OCR中识别的图号", 
    "scale": "从OCR中识别的比例",
    "project_name": "从OCR中识别的工程名称",
    "drawing_type": "根据内容判断的图纸类型"
  },
  "component_ids": ["KL1", "KZ1", "KB1"],
  "component_types": ["框架梁", "框架柱", "板"],
  "material_grades": ["C30", "HRB400"],
  "axis_lines": ["A", "B", "1", "2"],
  "summary": {
    "total_components": 0,
    "main_structure_type": "钢筋混凝土结构",
    "complexity_level": "中等"
  }
}
```

### 2. 最终输出结果保存

**保存位置**: 双轨协同分析的最终返回结果中

```python
final_result = {
    # 输出点1: OCR识别块 - 轨道1的结果
    "ocr_recognition_display": {
        "drawing_basic_info": self.global_drawing_overview.get("drawing_info", {}),
        "component_overview": {
            "component_ids": self.global_drawing_overview.get("component_ids", []),
            "component_types": self.global_drawing_overview.get("component_types", []),
            "material_grades": self.global_drawing_overview.get("material_grades", []),
            "axis_lines": self.global_drawing_overview.get("axis_lines", []),
            "summary": self.global_drawing_overview.get("summary", {})
        },
        "ocr_source_info": {
            "total_slices": len(self.enhanced_slices),
            "ocr_text_count": global_overview_result.get("ocr_text_count", 0),
            "analysis_method": "基于智能切片OCR汇总的GPT分析"
        }
    },
    # 全图概览数据
    "global_overview": self.global_drawing_overview
}
```

### 3. OpenAI交互记录保存

**保存位置**: Sealos云存储 - OpenAI会话记录

- **路径**: `openai_logs/{drawing_id}/`
- **文件名**: `openai_interaction_{session_id}.json_{hash}.txt`
- **内容**: 包含完整的API调用记录，包括轨道1的OCR清洗过程

**记录内容**:
```json
{
  "api_calls": [
    {
      "call_id": "call_xxx",
      "model": "gpt-4o-2024-11-20",
      "request_time": "2025-06-22T14:xx:xx",
      "messages": [
        {
          "role": "system",
          "content": "专业结构工程师，分析建筑图纸OCR文本"
        },
        {
          "role": "user", 
          "content": "OCR文本内容汇总..."
        }
      ],
      "response": {
        "content": "清洗后的结构化JSON结果"
      }
    }
  ]
}
```

### 4. 前端显示保存

**保存位置**: 前端React组件状态

- **组件**: `OCRRecognitionDisplay` 组件
- **状态**: `ocrData` 状态变量
- **显示**: 图纸基本信息、构件概览、材料等级等

## 数据传递路径

```
1. PaddleOCR扫描 → slice_info.ocr_results (每个切片)
2. OCR汇总 → combined_text (临时变量)
3. OpenAI清洗 → overview_data (GPT响应)
4. 内存保存 → self.global_drawing_overview (类变量)
5. 最终输出 → final_result["ocr_recognition_display"] (返回结果)
6. 前端显示 → ocrData (React状态)
7. 会话记录 → Sealos存储 (持久化)
```

## 关键特点

### 1. 多层次保存
- **运行时**: 类实例变量 `self.global_drawing_overview`
- **输出结果**: `final_result["ocr_recognition_display"]`
- **前端状态**: React组件状态
- **持久化**: Sealos云存储的会话记录

### 2. 结构化清洗
- **原始数据**: 24个切片的分散OCR文本
- **汇总数据**: 合并后的完整文本
- **清洗结果**: 结构化的JSON格式图纸信息

### 3. 实时可访问
- **分析过程中**: 通过 `self.global_drawing_overview` 访问
- **分析完成后**: 通过返回结果的 `ocr_recognition_display` 字段访问
- **前端显示**: 通过API响应实时更新界面

## 总结

**轨道1的PaddleOCR汇总结果经OpenAI清洗后的保存位置**：

1. **主要位置**: `self.global_drawing_overview` (类实例变量)
2. **输出位置**: `final_result["ocr_recognition_display"]` (最终返回结果)
3. **前端位置**: React组件的 `ocrData` 状态
4. **持久化位置**: Sealos云存储的OpenAI会话记录文件

这些数据在整个分析流程中保持可访问状态，并最终通过前端界面展示给用户。 