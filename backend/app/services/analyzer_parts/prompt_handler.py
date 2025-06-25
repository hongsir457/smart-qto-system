import logging
from typing import Dict, Any, List

from ..enhanced_slice_models import EnhancedSliceInfo

logger = logging.getLogger(__name__)


class PromptHandler:
    """处理与AI分析相关的提示词构建逻辑"""

    def build_global_overview_prompt(self, ocr_plain_text: str, drawing_info: Dict[str, Any]) -> str:
        """为全图OCR概览构建Prompt（只用纯文本）"""
        truncation_note = "\n...(文本过长，已截断)" if len(ocr_plain_text) > 4000 else ""
        drawing_name = drawing_info.get('drawing_name', '未知')
        drawing_type = drawing_info.get('drawing_type', '建筑图纸')
        
        prompt = f"""
你是一位专业的建筑工程量计算专家。请分析以下从建筑图纸中提取的OCR文本（已按顺序排序、相邻合并），并提供结构化的全图概览信息。

图纸信息：
- 文件名：{drawing_name}
- 图纸类型：{drawing_type}

OCR提取的纯文本内容：
{ocr_plain_text[:4000]}{truncation_note}

请按以下JSON格式返回分析结果：
{{
    "drawing_info": {{
        "project_name": "工程名称",
        "drawing_type": "图纸类型",
        "scale": "图纸比例",
        "drawing_number": "图纸编号"
    }},
    "component_ids": ["构件编号列表"],
    "component_types": ["构件类型列表"],
    "material_grades": ["材料等级列表"],
    "axis_lines": ["轴线标识列表"],
    "summary": {{
        "total_components": 0,
        "main_structure_type": "主要结构类型",
        "drawing_complexity": "图纸复杂程度"
    }}
}}

要求：
1. 准确识别图纸中的构件编号（如：KL1、Z1、B1等）
2. 识别构件类型（如：框架梁、柱、板等）
3. 提取材料等级信息（如：C30、HRB400等）
4. 识别轴线标识（如：A、B、C、1、2、3等）
5. 返回标准JSON格式，不要包含其他说明文字
"""
        return prompt

    def generate_enhanced_prompt(self, analyzer, slice_info: EnhancedSliceInfo) -> str:
        """生成OCR增强的Vision分析提示（包含全图概览信息）"""
        if not slice_info.ocr_results:
            return ""
        
        # 按类别组织OCR结果
        categorized_items = {}
        for ocr_item in slice_info.ocr_results:
            category = ocr_item.category
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(ocr_item)
        
        # 生成引导提示
        prompt_parts = []
        
        # 全图概览信息
        if hasattr(analyzer, 'global_drawing_overview') and analyzer.global_drawing_overview:
            overview = analyzer.global_drawing_overview
            prompt_parts.append("🌍 全图概览信息：")
            
            drawing_info = overview.get('drawing_info', {})
            if drawing_info:
                prompt_parts.append(f"- 图纸类型: {drawing_info.get('drawing_type', '未知')}")
                prompt_parts.append(f"- 工程名称: {drawing_info.get('project_name', '未知')}")
                prompt_parts.append(f"- 图纸比例: {drawing_info.get('scale', '未知')}")
            
            component_ids = overview.get('component_ids', [])
            if component_ids:
                prompt_parts.append(f"- 全图构件编号: {', '.join(component_ids[:10])}{'...' if len(component_ids) > 10 else ''}")
            
            component_types = overview.get('component_types', [])
            if component_types:
                prompt_parts.append(f"- 主要构件类型: {', '.join(component_types)}")
            
            material_grades = overview.get('material_grades', [])
            if material_grades:
                prompt_parts.append(f"- 材料等级: {', '.join(material_grades)}")
            
            axis_lines = overview.get('axis_lines', [])
            if axis_lines:
                prompt_parts.append(f"- 轴线编号: {', '.join(axis_lines[:8])}{'...' if len(axis_lines) > 8 else ''}")
            
            summary = overview.get('summary', {})
            if summary:
                prompt_parts.append(f"- 复杂程度: {summary.get('complexity_level', '未知')}")
            
            prompt_parts.append("")
        
        tile_pos = f"第{slice_info.row}行第{slice_info.col}列"
        prompt_parts.append(f"📄 当前图像为结构图切片（{tile_pos}），尺寸 {slice_info.width}x{slice_info.height}")
        
        if categorized_items:
            prompt_parts.append("\n🔍 当前切片OCR识别的构件信息：")
            
            category_names = {
                "component_id": "构件编号",
                "dimension": "尺寸规格",
                "material": "材料等级",
                "axis": "轴线位置"
            }
            
            for category, items in categorized_items.items():
                if category == "unknown":
                    continue
                    
                category_name = category_names.get(category, category)
                texts = [item.text for item in items]
                
                if texts:
                    prompt_parts.append(f"- {category_name}: {', '.join(texts)}")
        
        prompt_parts.append("\n👁️ Vision构件识别要求（重点：几何形状，非文本）：")
        prompt_parts.append("1. 🔍 OCR文本匹配：将OCR识别的构件编号与图像中的构件进行匹配")
        prompt_parts.append("2. 🌍 全图上下文：结合全图构件清单，理解当前切片的构件分布")
        prompt_parts.append("3. 📐 几何形状识别：识别梁（矩形）、柱（圆形/方形）、板（面状）、墙（线状）等")
        prompt_parts.append("4. 📏 尺寸测量：基于图纸比例计算构件的实际尺寸（长宽高厚）")
        prompt_parts.append("5. 🔗 连接关系：识别构件间的连接和支撑关系")
        prompt_parts.append("6. 📊 工程量数据：提供面积、体积等工程量计算所需的几何参数")
        
        prompt_parts.append("\n📋 返回JSON格式，重点包含：")
        prompt_parts.append("- 构件几何形状和精确尺寸（用于工程量计算）")
        prompt_parts.append("- 构件边界框和空间位置")
        prompt_parts.append("- 构件结构作用和连接关系")
        prompt_parts.append("- OCR文本与Vision构件的匹配关系")
        prompt_parts.append("注意：专注构件识别，不要重复OCR的文本识别工作")
        
        return "\n".join(prompt_parts)

    def generate_basic_vision_prompt(self, analyzer, slice_info: EnhancedSliceInfo, drawing_info: Dict[str, Any]) -> str:
        """生成基础Vision分析提示（包含全图概览，但无单切片OCR增强）"""
        tile_pos = f"第{slice_info.row}行第{slice_info.col}列"
        
        prompt_parts = []
        
        if hasattr(analyzer, 'global_drawing_overview') and analyzer.global_drawing_overview:
            overview = analyzer.global_drawing_overview
            prompt_parts.append("🌍 全图概览信息：")
            
            drawing_info_overview = overview.get('drawing_info', {})
            if drawing_info_overview:
                prompt_parts.append(f"- 图纸类型: {drawing_info_overview.get('drawing_type', '未知')}")
                prompt_parts.append(f"- 工程名称: {drawing_info_overview.get('project_name', '未知')}")
                prompt_parts.append(f"- 图纸比例: {drawing_info_overview.get('scale', '未知')}")
            
            component_ids = overview.get('component_ids', [])
            if component_ids:
                prompt_parts.append(f"- 全图构件编号: {', '.join(component_ids[:10])}{'...' if len(component_ids) > 10 else ''}")
            
            component_types = overview.get('component_types', [])
            if component_types:
                prompt_parts.append(f"- 主要构件类型: {', '.join(component_types)}")
            
            material_grades = overview.get('material_grades', [])
            if material_grades:
                prompt_parts.append(f"- 材料等级: {', '.join(material_grades)}")
            
            prompt_parts.append("")
        
        prompt_parts.append(f"📄 当前图像为结构图切片（{tile_pos}）")
        prompt_parts.append(f"图纸比例：{drawing_info.get('scale', '1:100')}，图号 {drawing_info.get('drawing_number', 'Unknown')}")
        prompt_parts.append("")
        
        prompt_parts.append("请进行构件几何识别分析（重点：形状和尺寸，非文本）：")
        prompt_parts.append("- 识别构件几何形状：梁（矩形）、柱（圆形/方形）、板（面状）、墙（线状）")
        prompt_parts.append("- 测量构件精确尺寸：长度、宽度、高度、厚度（基于图纸比例）")
        prompt_parts.append("- 确定构件空间位置：边界框坐标、轴线位置")
        prompt_parts.append("- 分析构件连接关系：与其他构件的连接和支撑")
        prompt_parts.append("- 计算工程量参数：面积、体积等几何数据")
        prompt_parts.append("")
        prompt_parts.append("注意：专注构件的几何特征识别，为工程量计算提供数据")
        prompt_parts.append("返回JSON格式，包含详细的几何参数和工程量数据。")
        
        return "\n".join(prompt_parts) 