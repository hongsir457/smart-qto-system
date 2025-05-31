# ChatGPT智能工程量分析系统

## 概述

本系统采用ChatGPT-4 Vision模型，实现施工图的智能识别和工程量自动计算。通过AI技术替代传统的规则引擎，大幅提升识别准确性和适应性。

## 核心特性

### 🎯 智能识别
- **多专业支持**: 建筑、结构、机电等各专业施工图
- **标准化解析**: 基于GB/T制图规范和平法图集
- **高精度识别**: 构件类型、尺寸、数量、材料等级等
- **上下文理解**: 结合项目背景信息提升识别准确性

### 📊 工程量计算
- **规范依据**: 严格按照GB50500-2013工程量清单计价规范
- **项目分类**: 按工程量清单项目编码自动分类统计
- **计算公式**: 提供详细的工程量计算依据和公式
- **质量验证**: AI自动复查计算内容的完整性和准确性

### 🔄 智能处理
- **多页合并**: 自动合并多页图纸的分析结果
- **去重优化**: 智能识别和合并相同构件
- **置信度评估**: 提供分析结果的可信度评分
- **异常检测**: 标识缺失信息和需要人工核实的项目

## 系统架构

```
用户上传PDF图纸
       ↓
PDF转高质量图像 (300 DPI)
       ↓
构建专业提示词 (含项目上下文)
       ↓
ChatGPT-4V视觉分析
       ↓
JSON结构化结果
       ↓
多页结果合并去重
       ↓
Excel工程量清单导出
```

## API接口说明

### 1. 分析施工图PDF

**POST** `/api/v1/chatgpt-analysis/analyze-pdf`

#### 请求参数
- `pdf_file`: 施工图PDF文件 (multipart/form-data)
- `request_data`: JSON字符串，包含以下参数：

```json
{
  "api_key": "your-openai-api-key",
  "api_base": "https://api.openai.com/v1",
  "project_context": {
    "project_name": "某住宅小区A栋",
    "building_type": "住宅建筑",
    "structure_type": "框架剪力墙结构",
    "design_stage": "施工图设计",
    "special_requirements": "抗震设防烈度8度"
  }
}
```

#### 响应结果
```json
{
  "task_id": "uuid-task-id",
  "status": "processing"
}
```

### 2. 查询分析状态

**GET** `/api/v1/chatgpt-analysis/analysis-status/{task_id}`

#### 响应结果（进行中）
```json
{
  "task_id": "uuid-task-id",
  "status": "processing"
}
```

#### 响应结果（完成）
```json
{
  "task_id": "uuid-task-id",
  "status": "completed",
  "result": {
    "project_info": {
      "project_name": "某住宅小区A栋",
      "design_unit": "某某建筑设计院",
      "drawing_name": "首层平面图",
      "drawing_number": "A-01",
      "scale": "1:100",
      "design_stage": "施工图设计"
    },
    "quantity_list": [
      {
        "sequence": 1,
        "drawing_number": "A-01",
        "component_type": "框架柱",
        "component_code": "KZ1",
        "component_count": 12,
        "section_size": "400×600",
        "project_code": "010401001",
        "project_name": "现浇钢筋混凝土柱",
        "unit": "m³",
        "quantity": 28.8,
        "calculation_formula": "12根×0.4×0.6×10m",
        "remarks": "C30混凝土，纵筋HRB400"
      }
    ],
    "summary": {
      "total_items": 1,
      "main_structure_volume": 28.8,
      "steel_reinforcement_weight": 0.0,
      "formwork_area": 0.0,
      "analysis_confidence": 0.92,
      "missing_information": []
    }
  },
  "excel_download_url": "/api/v1/chatgpt-analysis/download-excel/uuid-task-id"
}
```

### 3. 下载Excel工程量清单

**GET** `/api/v1/chatgpt-analysis/download-excel/{task_id}`

返回Excel文件下载

### 4. 删除分析任务

**DELETE** `/api/v1/chatgpt-analysis/analysis/{task_id}`

删除任务记录和相关文件

## 输出格式说明

### Excel工程量清单包含以下内容：

#### 项目信息区域
- 项目名称、设计单位、图纸名称
- 图号、比例、设计阶段

#### 工程量明细表
| 序号 | 图号 | 构件类型 | 构件编号 | 构件数量 | 截面尺寸 | 工程内容 | 计量单位 | 统计数量 | 计算依据 | 备注 |
|------|------|----------|----------|----------|----------|----------|----------|----------|----------|------|
| 1 | A-01 | 框架柱 | KZ1 | 12 | 400×600 | 现浇钢筋混凝土柱 | m³ | 28.8 | 12根×0.4×0.6×10m | C30混凝土 |

#### 汇总统计
- 统计项目总数
- 主体结构混凝土总量(m³)
- 钢筋总重量(kg)
- 模板总面积(m²)
- 分析置信度

## 使用指南

### 1. 环境配置

```bash
# 安装依赖
pip install PyMuPDF pillow pandas openpyxl requests

# 设置API密钥（方式一：环境变量）
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选
```

### 2. 图纸要求
- **格式**: PDF格式
- **清晰度**: 建议300 DPI以上扫描质量
- **内容**: 标准的施工图纸，包含图签、构件标注等
- **语言**: 支持中文制图规范

### 3. 最佳实践

#### 提供详细的项目上下文
```json
{
  "project_context": {
    "project_name": "具体项目名称",
    "building_type": "住宅/办公/商业/工业建筑",
    "structure_type": "框架/剪力墙/钢结构/混合结构",
    "design_stage": "方案/初设/施工图设计",
    "special_requirements": "抗震/人防/绿建等特殊要求"
  }
}
```

#### 图纸预处理建议
- 确保图纸扫描清晰，文字可读
- 图签信息完整
- 构件编号和尺寸标注清楚
- 避免图纸过度压缩

### 4. 结果验证
- 检查**置信度评分**（建议>0.8）
- 核对**缺失信息**列表
- 验证关键构件的**计算公式**
- 对置信度较低的项目进行人工复核

## 费用说明

### OpenAI API调用费用（参考）
- **GPT-4 Vision**: 约$0.01-0.04/张图片（根据分辨率）
- **建议配置**: 设置usage limits防止超支
- **优化建议**: 
  - 合理设置图像分辨率
  - 批量处理相似图纸
  - 使用项目上下文减少重复分析

## 限制说明

### 技术限制
- 单次最大图像尺寸: 2048×2048像素
- 支持的图纸类型: 二维施工图（不支持3D模型）
- API超时限制: 120秒/请求

### 识别限制
- 手绘草图识别精度较低
- 非标准制图规范可能识别困难
- 复杂装配图需要人工辅助验证

## 故障排除

### 常见问题

#### 1. API密钥错误
```
错误: 必须提供OpenAI API密钥
解决: 检查环境变量或请求参数中的API密钥
```

#### 2. 图像转换失败
```
错误: PDF转换为图像失败
解决: 确保安装了PyMuPDF: pip install PyMuPDF
```

#### 3. 识别精度低
```
问题: 分析置信度<0.5
解决: 
- 提供更清晰的图纸
- 补充详细的项目上下文
- 检查图纸是否符合制图规范
```

#### 4. Excel导出失败
```
错误: Excel导出失败
解决: 确保安装了openpyxl: pip install openpyxl
```

### 性能优化

#### 提升识别准确性
1. **高质量图纸**: 使用300 DPI以上扫描
2. **标准制图**: 遵循GB/T制图规范
3. **完整信息**: 确保图签和标注完整
4. **项目上下文**: 提供详细的项目背景

#### 降低API费用
1. **合理分辨率**: 避免过高的图像分辨率
2. **批量处理**: 相似图纸使用相同上下文
3. **结果缓存**: 避免重复分析同一图纸

## 开发扩展

### 自定义提示词
可以修改`ChatGPTQuantityAnalyzer`类中的`quantity_prompt_template`来适应特定需求：

```python
# 添加特定专业的识别要求
custom_prompt = """
在原有提示词基础上，增加以下要求：
1. 特别关注给排水管道的管径和长度
2. 识别电气设备的型号和数量
3. 计算暖通风管的面积和材料
"""
```

### 集成第三方服务
- **结果验证**: 集成专业造价软件API
- **图纸管理**: 对接BIM平台
- **审核流程**: 集成企业OA系统

## 更新日志

### v1.0.0 (当前版本)
- ✅ 基础的PDF图纸分析功能
- ✅ ChatGPT-4V智能识别
- ✅ Excel工程量清单导出
- ✅ 多页结果合并
- ✅ 置信度评估
- ✅ RESTful API接口

### 规划中的功能
- 🔄 支持更多图纸格式(DWG, DXF)
- 🔄 批量处理多个项目
- 🔄 历史记录和对比分析
- 🔄 与BIM模型数据融合
- 🔄 移动端APP支持

---

> **免责声明**: 本系统基于AI技术提供工程量分析，结果仅供参考。正式工程项目中请结合专业人员审核确认。AI分析可能存在误差，用户需承担使用风险。 