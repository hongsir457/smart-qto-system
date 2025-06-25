# -*- coding: utf-8 -*-
"""
AI Prompt Builder - 提示词构建器
从ai_analyzer.py中提取出来的提示词构建功能
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self):
        logger.info(" PromptBuilder initialized")
    
    def build_system_prompt(self) -> str:
        """构建指导LLM行为的系统级Prompt"""
        return """
        # 角色定义
        你是一名国家一级注册建造师和高级造价工程师，具有20年建筑工程量清单编制经验。
        你精通《建筑工程工程量计算规范》(GB50854)、《房屋建筑与装饰工程工程量计算规范》(GB50854)等国家标准。

        # 核心任务
        分析建筑图纸OCR识别数据，按照国家工程量计算规范生成标准化的工程量清单（QTO）。

        # 数据分析优先级
        1. **结构化表格数据** - 最高优先级，经过预处理的准确数据
        2. **零散文本数据** - 辅助信息，用于补充和验证表格数据
        3. **逻辑推理** - 基于工程经验填补合理信息

        # 工程量计算原则
        ## 构件分类标准：
        - **基础类**：独立基础、条形基础、筏板基础、桩基础
        - **结构类**：框架柱、剪力墙、框架梁、楼板、楼梯
        - **围护类**：外墙、内墙、门窗、栏杆

        # 输出JSON结构规范
        {
            "project_info": {"project_name": "", "drawing_number": "", "design_unit": ""},
            "components": [
                {
                    "component_id": "构件编号",
                    "component_type": "构件类型",
                    "dimensions": {"length": "", "width": "", "height": ""},
                    "quantity": 1,
                    "unit": "单位"
                }
            ]
        }

        # 重要要求
        1. 必须基于真实的图纸数据，不要生成模拟或示例数据
        2. 构件编号必须与图纸实际标注一致
        3. 如果某些信息不清晰，标注为"待确认"而不是猜测
        4. 确保JSON格式正确且可解析
        """
    
    def build_user_prompt(self, data: Dict[str, Any]) -> Optional[str]:
        """构建用户提示词"""
        try:
            prompt_parts = []
            
            # OCR文本数据
            ocr_texts = data.get("ocr_texts", [])
            if ocr_texts:
                prompt_parts.append("## OCR识别的文本数据:")
                for i, text in enumerate(ocr_texts[:50]):  # 限制数量
                    prompt_parts.append(f"{i+1}. {text}")
            
            # 表格数据
            tables = data.get("tables", [])
            if tables:
                prompt_parts.append("\n## 识别的表格数据:")
                for i, table in enumerate(tables[:10]):
                    prompt_parts.append(f"表格{i+1}: {table}")
            
            # 添加分析要求
            if prompt_parts:
                prompt_parts.append("\n## 分析要求:")
                prompt_parts.append("请基于以上图纸数据，生成标准化的工程量清单JSON。")
                prompt_parts.append("注意：只分析实际存在的数据，不要添加模拟内容。")
                
                return "\n".join(prompt_parts)
            else:
                return None
                
        except Exception as e:
            logger.error(f"构建用户提示词失败: {e}")
            return None
    
    def build_vision_prompt(self, step_name: str, context: str = "") -> str:
        """构建视觉分析提示词"""
        base_prompt = f"""
        你是专业的建筑图纸分析师。
        
        当前任务: {step_name}
        
        {context}
        
        请仔细分析图像，返回JSON格式的结构化数据。
        """
        
        return base_prompt.strip()
