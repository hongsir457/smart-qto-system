#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI提示词构建器组件
负责构建各种场景下的提示词模板
"""
import logging
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

class PromptBuilder:
    """提示词构建器"""
    
    def build_system_prompt(self) -> str:
        """构建指导LLM行为的系统级Prompt（用于OCR数据分析）"""
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

        ## 计量规则：
        - **混凝土构件**：按体积计算（m³），扣除钢筋和预埋件体积
        - **钢筋工程**：按重量计算（kg），分主筋、箍筋、构造筋
        - **模板工程**：按接触面积计算（m²）
        - **砌体工程**：按净体积计算（m³），扣除门窗洞口

        # 输出JSON结构规范
        ```json
        {
            "project_info": {
                "project_name": "项目名称（从图签提取）",
                "drawing_number": "图纸编号",
                "design_unit": "设计单位",
                "drawing_date": "出图日期",
                "scale": "图纸比例"
            },
            "components": [
                {
                    "component_id": "构件编号（如KZ1、L1等）",
                    "component_type": "构件类型（柱、梁、板、墙等）",
                    "structural_type": "结构类型（框架柱、框架梁、现浇板等）",
                    "dimensions": {
                        "length": "长度(mm)",
                        "width": "宽度(mm)", 
                        "height": "高度(mm)",
                        "thickness": "厚度(mm)"
                    },
                    "concrete": {
                        "grade": "混凝土强度等级（如C30）",
                        "volume": "混凝土体积(m³)"
                    },
                    "reinforcement": {
                        "main_bars": "主筋规格（如4Φ25）",
                        "stirrups": "箍筋规格（如Φ8@200）",
                        "total_weight": "钢筋总重量(kg)"
                    },
                    "formwork_area": "模板面积(m²)",
                    "location": "构件位置描述",
                    "quantity": "构件数量",
                    "unit": "计量单位",
                    "notes": "特殊说明"
                }
            ],
            "quantity_summary": {
                "concrete_total": "混凝土总量(m³)",
                "reinforcement_total": "钢筋总量(kg)",
                "formwork_total": "模板总面积(m²)",
                "component_count": "构件总数"
            },
            "analysis_metadata": {
                "data_quality": "数据质量评估（优/良/一般/差）",
                "confidence_level": "分析置信度（高/中/低）",
                "missing_info": ["缺失信息列表"],
                "assumptions": ["分析假设列表"],
                "warnings": ["注意事项列表"]
            }
        }
        ```

        # 质量控制要求
        1. **数据真实性**：严格基于提供的OCR数据，不得编造信息
        2. **计算准确性**：遵循国家计算规范，确保工程量计算正确
        3. **信息完整性**：尽可能提取所有有效信息，标注缺失项
        4. **格式标准化**：严格按照JSON格式要求输出
        5. **工程合理性**：确保构件尺寸、配筋等符合工程实际

        # 异常处理机制
        - 数据不清晰时：标注"数据不清晰"，给出可能的范围值
        - 信息缺失时：标注"信息缺失"，列出所需补充信息
        - 数据矛盾时：标注"数据矛盾"，选择更可靠的数据源
        - 规范冲突时：优先采用最新国家标准

        请严格按照以上要求进行分析，确保输出的工程量清单符合国家标准和工程实际。
        """

    def build_enhanced_system_prompt(self) -> str:
        """构建增强的系统级Prompt（用于Vision图纸分析），确保真实性和准确性"""
        return """
        # 专业角色
        你是一名国家一级注册建造师和高级造价工程师，拥有20年建筑工程图纸识读和工程量计算经验。
        你精通《建筑工程工程量计算规范》(GB50854)、《混凝土结构设计规范》(GB50010)等国家标准。

        # 核心任务
        分析真实建筑施工图纸，基于图纸实际可见内容，生成准确的工程量清单（QTO）。

        # 🚨 CRITICAL REQUIREMENTS - 违反将导致分析失败
        ## 数据真实性原则（零容忍政策）：
        1. **仅基于可见内容**：只分析图纸上实际可见的文字、符号、标注
        2. **禁止编造数据**：绝对不允许生成示例、模拟或假想的信息
        3. **如实反映缺失**：图纸不清晰或信息缺失时，如实说明，不得猜测
        4. **避免通用称谓**：严禁使用"某项目"、"某建筑"、"标题栏显示的"等描述性语言
        5. **构件编号真实**：必须完全按照图纸标注，禁止任何规律性编号生成
        
        ## ZERO TOLERANCE - 以下行为将被视为严重错误：
        ❌ 使用"某建筑结构平面布置图"等通用标题
        ❌ 写"标题栏显示的项目名称"而不是实际名称
        ❌ 生成"K-1、K-2"等规律性构件编号
        ❌ 使用"图纸上标注的XXX"等描述性语言
        ❌ 当信息不清晰时编造合理的内容

        # 图纸识读步骤
        ## 第一步：图框信息提取
        1. 仔细查看图纸标题栏（通常位于右下角）
        2. 提取项目名称、图纸编号、设计单位、出图日期
        3. 识别图纸比例、图纸名称等基本信息
        4. 如标题栏不清晰，标注"标题栏模糊不清"

        ## 第二步：构件标注识别
        1. 逐个扫描图纸上的构件编号标注
        2. 识别构件类型符号（如KZ表示框架柱、L表示梁）
        3. 读取尺寸标注（长×宽×高或截面尺寸）
        4. 记录构件在图纸中的位置和轴线关系

        ## 第三步：配筋信息提取
        1. 识别钢筋符号（Φ、HRB400、C等）
        2. 读取主筋、箍筋规格和间距
        3. 提取钢筋保护层厚度信息
        4. 注意区分受力筋和构造筋

        ## 第四步：混凝土等级识别
        1. 查找混凝土强度等级标注（如C30、C35）
        2. 识别不同构件的混凝土等级差异
        3. 注意特殊部位的混凝土要求

        请严格按照以上要求分析图纸，确保输出的工程量清单真实、准确、符合国家标准。
        """

    def build_user_prompt(self, data: Dict[str, Any]) -> Optional[str]:
        """构建包含实际数据的用户级Prompt（用于OCR数据分析）"""
        
        # 提取零散文本
        texts = [item['text'] for item in data.get('texts', [])]
        all_text_str = "\n".join(texts)

        # 提取并格式化表格数据
        tables_str_list = []
        tables_json = data.get('tables_json', [])
        if tables_json:
            for i, table_json_str in enumerate(tables_json):
                try:
                    df = pd.read_json(table_json_str, orient='split')
                    # 转换为对LLM更友好的Markdown格式
                    tables_str_list.append(f"--- 表格 {i+1} ---\n{df.to_markdown(index=False)}\n")
                except Exception as e:
                    logger.warning(f"Could not parse a table from JSON for prompt: {e}")

        if not all_text_str and not tables_str_list:
            return None

        # 构建专业化的用户提示词
        prompt_parts = [
            "# 工程量清单分析任务",
            "",
            "## 任务说明",
            "请根据以下从建筑图纸中提取的OCR识别数据，按照《建筑工程工程量计算规范》(GB50854)生成标准化的工程量清单JSON。",
            "",
            "## 数据处理原则",
            "1. **表格数据优先**：结构化表格数据具有最高可信度，请以此为核心进行分析",
            "2. **文本数据辅助**：零散文本用于补充表格信息或提供上下文参考", 
            "3. **逻辑验证**：对提取的数据进行工程合理性验证",
            "4. **缺失标注**：如信息不足请明确标注，不要猜测补充",
            "",
            "## 分析要求",
            "- 严格按照国家工程量计算规范进行计算",
            "- 确保构件分类准确（基础、结构、围护）",
            "- 验证配筋率合理性（通常在1%-4%范围）",
            "- 检查尺寸单位一致性（统一为mm和m³）",
            "- 提供完整的质量评估和置信度分析",
            "",
            "---"
        ]

        # 添加结构化表格数据
        if tables_str_list:
            prompt_parts.extend([
                "## 📊 结构化表格数据（主要分析依据）",
                "",
                "以下表格数据已经过预处理，具有较高可信度，请作为工程量分析的主要依据：",
                ""
            ])
            prompt_parts.extend(tables_str_list)
            prompt_parts.append("---")
        else:
            prompt_parts.extend([
                "## 📊 结构化表格数据",
                "❌ 未检测到结构化表格数据",
                "⚠️ 请基于文本数据进行分析，但需要降低置信度评估",
                "",
                "---"
            ])

        # 添加零散文本数据  
        if all_text_str:
            text_lines = all_text_str.split('\n')
            # 过滤空行和无效文本
            filtered_lines = [line.strip() for line in text_lines if line.strip()]
            
            prompt_parts.extend([
                "## 📝 零散文本数据（辅助参考信息）",
                "",
                f"从图纸中识别的文本信息共 {len(filtered_lines)} 条，用于补充和验证表格数据：",
                "",
                "```"
            ])
            prompt_parts.extend(filtered_lines)
            prompt_parts.extend([
                "```", 
                "",
                "---"
            ])
        else:
            prompt_parts.extend([
                "## 📝 零散文本数据", 
                "❌ 未检测到有效文本信息",
                "",
                "---"
            ])
            
        # 添加分析指导
        prompt_parts.extend([
            "## 🔍 分析流程指导",
            "",
            "### 第一步：数据解读",
            "1. 识别图纸类型（平面图、配筋图、详图等）",
            "2. 提取项目基本信息（名称、编号、日期等）",
            "3. 分析数据完整性和可信度",
            "",
            "### 第二步：构件识别",
            "1. 根据编号规律识别构件类型（KZ-柱、L-梁、B-板等）", 
            "2. 提取构件尺寸信息（截面、长度、高度）",
            "3. 识别混凝土强度等级和钢筋配置",
            "",
            "### 第三步：工程量计算",
            "1. 按规范计算混凝土体积（扣除钢筋体积）",
            "2. 计算钢筋重量（主筋+箍筋+构造筋）",
            "3. 计算模板面积（按接触面积）",
            "",
            "## ⚠️ 重要提醒",
            "- 如遇到数据不清晰，请在对应字段标注'数据不清晰'",
            "- 如信息缺失，请标注'信息缺失'并说明缺失内容",
            "- 如数据存在矛盾，请选择更可靠的数据源并说明原因",
            "- 严格按照JSON格式要求输出，确保数据结构完整",
            "",
            "## 🎯 开始分析",
            "请基于以上数据和要求，生成符合国家标准的工程量清单JSON："
        ])
            
        return "\n".join(prompt_parts)

    def build_vision_step_prompt(self, step_name: str, context_data: Dict[str, Any] = None) -> str:
        """为废弃的五步Vision分析构建提示词"""
        logger.warning(f"⚠️ 五步Vision分析方法已废弃，请使用双轨协同分析")
        return f"步骤 {step_name} 已废弃，请使用双轨协同分析方法"

    def build_global_overview_prompt(self, all_ocr_texts: List[str], drawing_info: Dict[str, Any]) -> str:
        """构建全图OCR概览分析提示词"""
        return f"""
        # 建筑图纸全图OCR概览分析

        ## 任务目标
        基于图纸的完整OCR文本，提供图纸概览信息和构件分布概况。

        ## 图纸基本信息
        - 图纸ID: {drawing_info.get('drawing_id', 'unknown')}
        - 批次ID: {drawing_info.get('batch_id', 'unknown')}
        - 处理时间: {drawing_info.get('processing_time', 'unknown')}

        ## OCR文本数据
        以下是从图纸中提取的完整文本信息：

        ```
        {chr(10).join(all_ocr_texts[:100])}  # 限制显示前100行
        {"..." if len(all_ocr_texts) > 100 else ""}
        ```

        ## 分析要求
        请基于OCR文本提供以下概览信息：

        1. **图纸类型识别**：判断图纸类型（结构平面图、配筋图、详图等）
        2. **项目基本信息**：提取项目名称、图纸编号、设计单位等
        3. **构件类型概况**：识别出现的主要构件类型
        4. **技术参数概况**：主要的混凝土等级、钢筋规格等
        5. **图纸完整性评估**：评估OCR识别的完整性

        ## 输出格式
        请以JSON格式返回分析结果：
        {{
            "drawing_type": "图纸类型",
            "project_info": {{
                "project_name": "项目名称或无法识别",
                "drawing_number": "图纸编号或无法识别"
            }},
            "component_overview": {{
                "detected_types": ["检测到的构件类型列表"],
                "estimated_count": "估计构件总数"
            }},
            "technical_overview": {{
                "concrete_grades": ["检测到的混凝土等级"],
                "steel_grades": ["检测到的钢筋等级"]
            }},
            "ocr_quality": {{
                "completeness": "完整性评估（高/中/低）",
                "clarity": "清晰度评估（高/中/低）",
                "recommendations": ["改进建议"]
            }}
        }}
        """ 