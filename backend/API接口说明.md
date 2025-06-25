# 图纸分析API接口说明

## 概述

图纸分析系统提供了完整的两阶段分析流程：
- **一阶段分析**：基于PaddleOCR的结构化文本分析，提取构件编号、尺寸、图框信息等
- **二阶段分析**：结合PNG图纸和构件编号，使用大模型进行多轮对话深度分析

前端可以分别获取这两部分的分析结果，在图纸详情页面的不同区域展示。

## API接口列表

### 1. 获取OCR结果和一阶段分析结果

**接口路径：** `GET /api/v1/drawings/{drawing_id}/ocr-results`

**用途：** 获取图纸的OCR识别结果和一阶段结构化分析结果，用于在"OCR结果"区域展示。

**返回数据结构：**
```json
{
  "drawing_id": 123,
  "status": "completed",
  "ocr_data": {
    "text_regions": [
      {
        "text": "KZ1",
        "confidence": 0.95,
        "bbox": {
          "x_min": 100, "y_min": 100,
          "x_max": 150, "y_max": 130,
          "center_x": 125, "center_y": 115,
          "width": 50, "height": 30
        },
        "bbox_area": 1500.0,
        "text_length": 3,
        "is_number": false,
        "is_dimension": false,
        "is_component_code": true
      }
    ],
    "total_regions": 25,
    "all_text": "KZ1\n400×400\nKL1\n...",
    "statistics": {
      "total_count": 25,
      "numeric_count": 8,
      "dimension_count": 5,
      "component_code_count": 4,
      "avg_confidence": 0.89
    },
    "processing_time": 3.2
  },
  "stage_one_analysis": {
    "drawing_type": "结构",
    "title_block": {
      "project_name": "某住宅小区",
      "drawing_title": "结构施工图",
      "drawing_number": "S-01",
      "scale": "1:100"
    },
    "components": [
      {
        "code": "KZ1",
        "component_type": "框架柱",
        "dimensions": ["400×400"],
        "position": {"x": 125, "y": 115},
        "confidence": 0.95
      }
    ],
    "dimensions": [
      {
        "text": "400×400",
        "pattern": "(\\d+)×(\\d+)",
        "position": {"x": 180, "y": 115},
        "confidence": 0.92
      }
    ],
    "component_list": [
      {
        "code": "KZ1",
        "type": "框架柱",
        "dimensions": ["400×400"],
        "position": {"x": 125, "y": 115},
        "confidence": 0.95,
        "dimension_count": 1
      }
    ],
    "statistics": {
      "total_components": 4,
      "total_dimensions": 5,
      "avg_confidence": 0.89,
      "components_with_dimensions": 3
    }
  },
  "quality_info": {
    "avg_confidence": 0.89,
    "total_components_found": 4,
    "total_dimensions_found": 5,
    "drawing_type_identified": true
  }
}
```

**前端展示建议：**
- 在"OCR结果"标签页中展示 `ocr_data.text_regions`
- 显示识别到的文本、位置、置信度等信息
- 展示图纸基本信息（`stage_one_analysis.title_block`）
- 显示初步识别的构件列表（`stage_one_analysis.component_list`）

### 2. 获取二阶段分析结果（构件分析结果）

**接口路径：** `GET /api/v1/drawings/{drawing_id}/analysis-results`

**用途：** 获取二阶段AI深度分析结果，用于在"构件分析结果"区域展示。

**返回数据结构：**
```json
{
  "drawing_id": 123,
  "analysis_type": "stage_two",
  "has_ai_analysis": true,
  "components": [
    {
      "code": "KZ1",
      "type": "框架柱",
      "dimensions": {
        "section": "400×400",
        "height": "3600",
        "concrete_grade": "C30"
      },
      "material": {
        "concrete": "C30",
        "steel": "HRB400",
        "main_rebar": "8Φ20"
      },
      "quantity": 4,
      "position": {"floor": "1-3层", "grid": "A1"},
      "attributes": {
        "load_bearing": true,
        "seismic_grade": "二级",
        "fire_resistance": "1.5h"
      }
    }
  ],
  "analysis_summary": {
    "initial_summary": "识别到主要结构构件包括框架柱、框架梁等",
    "detail_summary": "详细分析了构件尺寸、材料等级",
    "verification_summary": "最终验证确认构件信息准确",
    "total_components": 12,
    "analysis_rounds": 3
  },
  "quality_assessment": {
    "overall_confidence": 0.92,
    "completeness": "高",
    "accuracy": "excellent"
  },
  "recommendations": [
    "建议核实KZ3柱的配筋详图",
    "注意检查梁柱连接节点的构造要求"
  ],
  "llm_analysis": {
    "model_used": "gpt-4o",
    "analysis_rounds": 3,
    "overall_confidence": 0.92,
    "conversation_history": [...]
  },
  "statistics": {
    "total_components": 12,
    "processing_time": 45.3,
    "ai_enhanced": true
  }
}
```

**前端展示建议：**
- 在"构件分析结果"标签页中展示详细的构件信息
- 显示AI分析的总结（`analysis_summary`）
- 展示质量评估和建议（`quality_assessment`, `recommendations`）
- 可选择性展示AI分析过程（`llm_analysis.conversation_history`）

### 3. 获取最终构件清单（统一接口）

**接口路径：** `GET /api/v1/drawings/{drawing_id}/components`

**用途：** 获取最终的构件清单，用于导出和总览。

**返回数据结构：**
```json
{
  "drawing_id": 123,
  "components": [...],  // 最终构件列表
  "total_count": 12,
  "analysis_info": {
    "source": "ai_enhanced",  // 或 "ocr_based"
    "has_ai_analysis": true,
    "stages_completed": ["png_conversion", "ocr_recognition", "stage_one_analysis", "stage_two_analysis"],
    "processing_time": 48.5
  },
  "quality_metrics": {
    "component_count": 12,
    "confidence_level": "high",  // 或 "medium"
    "analysis_depth": "detailed"  // 或 "basic"
  }
}
```

### 4. 获取处理状态

**接口路径：** `GET /api/v1/drawings/{drawing_id}/status`

**用途：** 实时获取图纸处理状态，用于进度显示。

## 前端展示方案建议

### 图纸详情页面布局

```
┌─────────────────────────────────────────┐
│                图纸信息                    │
├─────────────────────────────────────────┤
│  [OCR结果] [构件分析结果] [构件清单]      │
├─────────────────────────────────────────┤
│                                         │
│  OCR结果内容区域：                        │
│  - 识别到的文本列表                        │
│  - 图框信息                              │
│  - 初步构件识别                          │
│  - 识别质量统计                          │
│                                         │
└─────────────────────────────────────────┘
```

### OCR结果页面内容

1. **图框信息卡片**
   - 项目名称、图纸标题、图号等
   - 来源：`/ocr-results` -> `stage_one_analysis.title_block`

2. **文本识别结果**
   - 表格形式展示所有识别的文本
   - 显示文本内容、位置、置信度、类型
   - 来源：`/ocr-results` -> `ocr_data.text_regions`

3. **初步构件识别**
   - 展示OCR阶段识别的构件列表
   - 来源：`/ocr-results` -> `stage_one_analysis.component_list`

4. **识别质量指标**
   - 平均置信度、识别数量统计等
   - 来源：`/ocr-results` -> `quality_info`

### 构件分析结果页面内容

1. **AI分析总结**
   - 分析概述、关键发现
   - 来源：`/analysis-results` -> `analysis_summary`

2. **详细构件信息**
   - 表格形式展示所有构件的详细属性
   - 支持筛选、排序、搜索
   - 来源：`/analysis-results` -> `components`

3. **质量评估与建议**
   - 分析质量评分、改进建议
   - 来源：`/analysis-results` -> `quality_assessment`, `recommendations`

4. **AI分析过程（可选）**
   - 折叠面板展示多轮对话过程
   - 来源：`/analysis-results` -> `llm_analysis.conversation_history`

## 错误处理

### 常见错误情况

1. **图纸处理中**：返回处理状态和进度
2. **二阶段分析失败**：`/analysis-results` 返回一阶段结果作为备用
3. **处理结果解析失败**：返回适当的错误信息

### 前端处理建议

```javascript
// 获取OCR结果
async function fetchOCRResults(drawingId) {
  try {
    const response = await fetch(`/api/v1/drawings/${drawingId}/ocr-results`);
    if (response.ok) {
      return await response.json();
    } else {
      // 处理错误情况
      console.error('获取OCR结果失败:', response.status);
    }
  } catch (error) {
    console.error('网络错误:', error);
  }
}

// 获取构件分析结果
async function fetchAnalysisResults(drawingId) {
  try {
    const response = await fetch(`/api/v1/drawings/${drawingId}/analysis-results`);
    if (response.ok) {
      const data = await response.json();
      if (!data.has_ai_analysis) {
        // 显示警告：仅有基础分析结果
        showWarning('AI分析未完成，显示基础分析结果');
      }
      return data;
    }
  } catch (error) {
    console.error('获取分析结果失败:', error);
  }
}
```

## 总结

通过这套API接口设计，前端可以：

1. **分层展示分析结果**：OCR结果和AI分析结果分别展示
2. **渐进式信息展示**：先展示基础OCR结果，再展示深度AI分析
3. **灵活的错误处理**：当AI分析失败时，仍可展示基础分析结果
4. **丰富的数据支持**：提供足够的数据支持多样化的前端展示需求

这样的设计既满足了分别展示的需求，又保证了系统的健壮性和用户体验。 