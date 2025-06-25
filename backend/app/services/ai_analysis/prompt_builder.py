#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词构建器 - 负责构建各种AI分析提示词
"""
import logging
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class PromptBuilder:
    """
    负责构建AI分析所需的各种提示词
    """
    
    def __init__(self):
        """初始化提示词构建器"""
        logger.info("✅ PromptBuilder initialized")
    
    def build_system_prompt(self) -> str:
        """构建系统级提示词"""
        return """
你是一个专业的工程造价师助手，专门分析建筑结构图纸并生成工程量清单（QTO - Quantity Take-Off）。

你的任务是：
1. 分析提供的OCR文本和表格数据
2. 识别图纸中的结构构件（如梁、柱、板、墙等）
3. 提取每个构件的关键信息（编号、类型、尺寸、位置等）
4. 生成标准化的工程量清单

输出格式要求：
- 必须返回标准JSON格式
- 包含项目信息、构件清单、汇总统计
- 所有数值必须基于图纸实际内容，严禁虚构

重要原则：
- 严格按照实际图纸内容提取信息
- 不得生成虚假或模拟数据
- 如信息不明确，标记为"待确认"
- 构件编号必须与图纸一致
"""

    def build_enhanced_system_prompt(self) -> str:
        """构建增强版系统提示词，用于处理模拟数据问题"""
        return """
你是一个专业的建筑工程造价师，具有多年图纸分析经验。现在需要你分析建筑结构图纸并生成准确的工程量清单。

【关键要求】
1. 必须严格基于图纸实际内容进行分析
2. 绝对禁止生成任何虚构、示例或模拟数据
3. 如果图纸信息不清晰，请标注"信息不明确"而非猜测
4. 构件编号必须完全按照图纸标注，不得自行编造

【常见错误避免】
- 不要使用"某建筑工程"、"示例项目"等通用名称
- 不要生成KZ-1、KZ-2、L-1、L-2等规律性编号
- 不要编造规整的尺寸数据
- 项目名称必须来自图纸标题栏实际内容

【输出格式】
返回标准JSON格式，包含：
- drawing_info: 图纸基本信息（必须来自标题栏）
- components: 构件清单（编号、类型、尺寸、位置）
- summary: 统计汇总

如果无法识别足够信息，请在相应字段标注具体原因。
"""

    def build_user_prompt(self, data: Dict[str, Any]) -> Optional[str]:
        """构建用户提示词"""
        if not data:
            return None
            
        prompt_parts = ["请分析以下建筑图纸数据：\n"]
        
        # 1. 处理OCR文本数据
        if 'ocr_text' in data and data['ocr_text']:
            prompt_parts.append("【OCR识别文本】")
            if isinstance(data['ocr_text'], list):
                for i, text_block in enumerate(data['ocr_text'], 1):
                    prompt_parts.append(f"{i}. {text_block}")
            else:
                prompt_parts.append(str(data['ocr_text']))
            prompt_parts.append("")
        
        # 2. 处理表格数据
        if 'tables' in data and data['tables']:
            prompt_parts.append("【表格数据】")
            for i, table in enumerate(data['tables'], 1):
                prompt_parts.append(f"表格 {i}:")
                if isinstance(table, dict):
                    table_str = json.dumps(table, ensure_ascii=False, indent=2)
                else:
                    table_str = str(table)
                prompt_parts.append(table_str)
            prompt_parts.append("")
        
        # 3. 处理其他结构化数据
        other_data = {k: v for k, v in data.items() 
                     if k not in ['ocr_text', 'tables'] and v}
        if other_data:
            prompt_parts.append("【其他识别数据】")
            for key, value in other_data.items():
                prompt_parts.append(f"{key}: {value}")
            prompt_parts.append("")
        
        # 4. 添加分析要求
        prompt_parts.extend([
            "请根据以上信息生成工程量清单，要求：",
            "1. 严格按照图纸实际内容进行分析",
            "2. 不得添加任何虚构或示例数据",
            "3. 返回标准JSON格式",
            "4. 如信息不明确请明确标注"
        ])
        
        result = "\n".join(prompt_parts)
        logger.info(f"构建用户提示词，长度: {len(result)} 字符")
        return result
    
    def build_vision_step_prompt(self, step_name: str, previous_context: str = "") -> str:
        """构建视觉分析步骤的提示词"""
        base_prompts = {
            "step1_drawing_info": """
请分析图纸并提取基本信息：
1. 项目名称（从标题栏获取）
2. 图纸编号
3. 设计单位
4. 图纸比例
5. 绘制日期

返回JSON格式，如果某项信息不明确请标注"信息不明确"。
""",
            "step2_component_ids": """
请识别图纸中所有结构构件的编号：
1. 扫描整个图纸区域
2. 识别所有构件标注（如KZ1、L1、B1等）
3. 按构件类型分组统计
4. 记录构件在图纸中的大致位置

返回JSON格式，包含所有识别到的构件编号列表。
""",
            "step3_count_components": """
请统计各类构件的数量：
1. 基于之前识别的构件编号
2. 计算每种构件的出现次数
3. 区分不同尺寸规格的同类构件
4. 生成构件统计表

返回JSON格式的构件数量统计。
""",
            "step4_extract_positions": """
请提取构件的位置信息：
1. 确定每个构件在图纸中的坐标位置
2. 识别构件的朝向和布置方式
3. 分析构件之间的空间关系
4. 记录楼层信息（如适用）

返回JSON格式的构件位置数据。
""",
            "step5_extract_attributes": """
请提取构件的属性信息：
1. 构件尺寸（长、宽、高）
2. 材料类型和强度等级
3. 截面形状和规格
4. 其他技术参数

返回JSON格式的构件属性数据。
"""
        }
        
        prompt = base_prompts.get(step_name, "请分析图纸并提取相关信息。")
        
        if previous_context:
            prompt = f"基于之前的分析结果：\n{previous_context}\n\n{prompt}"
        
        return prompt
    
    def build_context_prompt(self, step_name: str, previous_results: Dict) -> str:
        """构建包含上下文的提示词"""
        context_parts = []
        
        if step_name == "step2" and "drawing_info" in previous_results:
            drawing_info = previous_results["drawing_info"]
            context_parts.append(f"项目名称: {drawing_info.get('project_name', '未知')}")
            context_parts.append(f"图纸编号: {drawing_info.get('drawing_number', '未知')}")
        
        elif step_name == "step3" and "component_ids" in previous_results:
            component_ids = previous_results["component_ids"]
            context_parts.append("已识别的构件编号:")
            for comp_type, ids in component_ids.items():
                context_parts.append(f"  {comp_type}: {', '.join(ids)}")
        
        elif step_name == "step4" and previous_results:
            context_parts.append("基于之前的分析结果，现在需要提取位置信息...")
        
        elif step_name == "step5" and previous_results:
            context_parts.append("基于之前的分析结果，现在需要提取属性信息...")
        
        if context_parts:
            return "\n".join(context_parts) + "\n\n"
        return ""
    
    def build_multi_turn_prompt(self, turn_number: int, context_data: Dict = None) -> str:
        """构建多轮对话的提示词"""
        if turn_number == 1:
            return self.build_system_prompt()
        
        prompts = {
            2: "基于第一轮分析，请进一步完善和验证构件信息。",
            3: "请对前面的分析结果进行整合和质量检查。",
            4: "生成最终的工程量清单，确保数据准确性。"
        }
        
        base_prompt = prompts.get(turn_number, "请继续分析并完善结果。")
        
        if context_data:
            context_str = json.dumps(context_data, ensure_ascii=False, indent=2)
            return f"上一轮分析结果：\n{context_str}\n\n{base_prompt}"
        
        return base_prompt 