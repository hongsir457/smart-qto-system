#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉分析器 - 负责图像的视觉分析和多轮对话
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class VisionAnalyzer:
    """
    负责图像的视觉分析和多轮对话处理
    """
    
    def __init__(self, client, interaction_logger, prompt_builder):
        """初始化视觉分析器"""
        self.client = client
        self.interaction_logger = interaction_logger
        self.prompt_builder = prompt_builder
        logger.info("✅ VisionAnalyzer initialized")
    
    def prepare_images(self, image_paths: List[str]) -> List[Dict]:
        """准备图像数据供Vision API使用"""
        import base64
        encoded_images = []
        
        for image_path in image_paths:
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                    encoded_images.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    })
                logger.info(f"✅ 编码图片: {image_path}")
            except Exception as e:
                logger.error(f"❌ 图片编码失败 {image_path}: {e}")
        
        return encoded_images
    
    def execute_multi_turn_analysis(self, encoded_images: List[Dict], 
                                  task_id: str = None, drawing_id: int = None) -> Dict[str, Any]:
        """执行多轮分析"""
        if not self.client:
            return {"error": "OpenAI client not available"}
        
        logger.info("🔄 开始多轮Vision分析...")
        
        try:
            # Turn 1: 基础分析
            turn1_result = self._execute_vision_step(
                "Turn1_基础分析",
                self.prompt_builder.build_system_prompt(),
                [{"type": "text", "text": "请分析这些建筑图纸图像，识别结构构件并提取基本信息。"}] + encoded_images,
                task_id, drawing_id
            )
            
            if "error" in turn1_result:
                return turn1_result
            
            # Turn 2: 详细分析
            context_prompt = self.prompt_builder.build_multi_turn_prompt(2, turn1_result.get("response"))
            turn2_result = self._execute_vision_step(
                "Turn2_详细分析",
                context_prompt,
                [{"type": "text", "text": "基于第一轮分析，请进一步完善构件信息和尺寸数据。"}] + encoded_images,
                task_id, drawing_id
            )
            
            if "error" in turn2_result:
                return turn1_result  # 返回第一轮结果作为备选
            
            # 合并结果
            final_result = self._merge_multi_turn_results([turn1_result, turn2_result])
            logger.info("✅ 多轮分析完成")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 多轮分析异常: {e}")
            return {"error": str(e)}
    
    def execute_multi_turn_analysis_with_context(self, encoded_images: List[Dict], 
                                               task_id: str = None, drawing_id: int = None) -> Dict[str, Any]:
        """执行带上下文的多轮分析（5步法）"""
        if not self.client:
            return {"error": "OpenAI client not available"}
        
        logger.info("🔄 开始5步上下文分析...")
        analysis_results = {}
        
        try:
            # 初始化对话消息
            conversation_messages = []
            
            # Step 1: 提取图纸基本信息
            step1_result = self._execute_contextual_step_1(
                conversation_messages, encoded_images, task_id, drawing_id
            )
            analysis_results["step1_drawing_info"] = step1_result
            
            # Step 2: 识别构件编号
            step2_result = self._execute_contextual_step_2(
                conversation_messages, encoded_images, step1_result, task_id, drawing_id
            )
            analysis_results["step2_component_ids"] = step2_result
            
            # Step 3: 统计构件数量
            step3_result = self._execute_contextual_step_3(
                conversation_messages, encoded_images, step2_result, task_id, drawing_id
            )
            analysis_results["step3_component_counts"] = step3_result
            
            # Step 4: 提取位置信息
            step4_result = self._execute_contextual_step_4(
                conversation_messages, encoded_images, step3_result, task_id, drawing_id
            )
            analysis_results["step4_positions"] = step4_result
            
            # Step 5: 提取属性信息
            step5_result = self._execute_contextual_step_5(
                conversation_messages, encoded_images, step4_result, task_id, drawing_id
            )
            analysis_results["step5_attributes"] = step5_result
            
            # 综合生成最终QTO数据
            final_qto = self._synthesize_qto_data(analysis_results)
            logger.info("✅ 5步上下文分析完成")
            return final_qto
            
        except Exception as e:
            logger.error(f"❌ 上下文分析异常: {e}")
            return {"error": str(e)}
    
    def _execute_vision_step(self, step_name: str, system_prompt: str, user_content: List[Dict], 
                           task_id: str = None, drawing_id: int = None) -> Dict[str, Any]:
        """执行单个Vision分析步骤"""
        try:
            logger.info(f"📤 执行Vision步骤: {step_name}")
            
            from app.core.config import settings
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content
            
            # 记录交互
            if self.interaction_logger:
                try:
                    self.interaction_logger.log_api_call(
                        session_id=f"{task_id}_{step_name}",
                        step_name=step_name,
                        request_data={
                            "model": settings.OPENAI_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": "图像分析请求"}
                            ]
                        },
                        response_data={"content": response_content},
                        task_id=task_id,
                        drawing_id=drawing_id
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 交互记录失败: {e}")
            
            # 解析响应
            try:
                parsed_response = json.loads(response_content)
                logger.info(f"✅ {step_name} 执行成功")
                return {"success": True, "response": parsed_response}
            except json.JSONDecodeError:
                logger.warning(f"⚠️ {step_name} JSON解析失败，返回原始内容")
                return {"success": True, "response": response_content, "raw": True}
            
        except Exception as e:
            logger.error(f"❌ {step_name} 执行失败: {e}")
            return {"error": str(e)}
    
    def _execute_contextual_step_1(self, conversation_messages: List[Dict], 
                                  encoded_images: List[Dict], task_id: str, drawing_id: int) -> Dict[str, Any]:
        """执行第1步：提取图纸基本信息"""
        system_prompt = """
你是专业的建筑图纸分析师。请仔细分析图纸并提取以下基本信息：

1. 项目名称（从标题栏中提取，不要编造）
2. 图纸编号
3. 设计单位  
4. 图纸比例
5. 绘制日期
6. 图纸类型（结构图、建筑图等）

要求：
- 严格按照图纸实际内容提取
- 如果信息不清晰或无法识别，请标注"信息不明确"
- 绝对不要编造或假设任何信息
- 返回标准JSON格式
"""
        
        user_content = [
            {"type": "text", "text": "请分析图纸标题栏和基本信息"}
        ] + encoded_images
        
        conversation_messages.append({"role": "system", "content": system_prompt})
        conversation_messages.append({"role": "user", "content": user_content})
        
        return self._make_contextual_api_call("Step1_图纸信息", conversation_messages, task_id, drawing_id)
    
    def _execute_contextual_step_2(self, conversation_messages: List[Dict],
                                  encoded_images: List[Dict], previous_results: Dict,
                                  task_id: str, drawing_id: int) -> Dict[str, Any]:
        """执行第2步：识别构件编号"""
        context = self.prompt_builder.build_context_prompt("step2", previous_results)
        
        system_prompt = f"""
{context}

现在请识别图纸中所有结构构件的编号：

1. 扫描整个图纸，寻找构件标注
2. 识别柱子编号（如KZ1, KZ2等）
3. 识别梁编号（如L1, L2等）  
4. 识别板编号（如B1, B2等）
5. 识别其他构件编号

要求：
- 只记录图纸上实际存在的编号
- 按构件类型分组
- 不要生成规律性编号序列
- 返回JSON格式
"""
        
        user_content = [
            {"type": "text", "text": "请识别所有构件编号"}
        ] + encoded_images
        
        conversation_messages.append({"role": "user", "content": user_content})
        
        return self._make_contextual_api_call("Step2_构件编号", conversation_messages, task_id, drawing_id)
    
    def _execute_contextual_step_3(self, conversation_messages: List[Dict],
                                  encoded_images: List[Dict], previous_results: Dict,
                                  task_id: str, drawing_id: int) -> Dict[str, Any]:
        """执行第3步：统计构件数量"""
        context = self.prompt_builder.build_context_prompt("step3", previous_results)
        
        system_prompt = f"""
{context}

基于已识别的构件编号，请统计各类构件的数量：

1. 统计每种构件编号的出现次数
2. 区分不同规格的同类构件
3. 生成构件数量汇总表
4. 验证统计的准确性

要求：
- 基于图纸实际情况统计
- 避免重复计数
- 返回JSON格式的统计结果
"""
        
        user_content = [
            {"type": "text", "text": "请统计构件数量"}
        ] + encoded_images
        
        conversation_messages.append({"role": "user", "content": user_content})
        
        return self._make_contextual_api_call("Step3_构件统计", conversation_messages, task_id, drawing_id)
    
    def _execute_contextual_step_4(self, conversation_messages: List[Dict],
                                  encoded_images: List[Dict], previous_results: Dict,
                                  task_id: str, drawing_id: int) -> Dict[str, Any]:
        """执行第4步：提取位置信息"""
        context = self.prompt_builder.build_context_prompt("step4", previous_results)
        
        system_prompt = f"""
{context}

请提取构件的位置信息：

1. 确定构件在图纸中的坐标位置
2. 识别构件的布置模式
3. 分析构件之间的关系
4. 记录楼层或区域信息

要求：
- 基于图纸实际布置
- 提供相对位置关系
- 返回JSON格式
"""
        
        user_content = [
            {"type": "text", "text": "请提取构件位置信息"}
        ] + encoded_images
        
        conversation_messages.append({"role": "user", "content": user_content})
        
        return self._make_contextual_api_call("Step4_位置信息", conversation_messages, task_id, drawing_id)
    
    def _execute_contextual_step_5(self, conversation_messages: List[Dict],
                                  encoded_images: List[Dict], previous_results: Dict,
                                  task_id: str, drawing_id: int) -> Dict[str, Any]:
        """执行第5步：提取属性信息"""
        context = self.prompt_builder.build_context_prompt("step5", previous_results)
        
        system_prompt = f"""
{context}

请提取构件的详细属性：

1. 构件尺寸（长、宽、高）
2. 截面规格
3. 材料强度等级
4. 其他技术参数

要求：
- 从图纸标注中提取实际数值
- 如无明确标注则标记"待确认"
- 返回JSON格式
"""
        
        user_content = [
            {"type": "text", "text": "请提取构件属性信息"}
        ] + encoded_images
        
        conversation_messages.append({"role": "user", "content": user_content})
        
        return self._make_contextual_api_call("Step5_属性信息", conversation_messages, task_id, drawing_id)
    
    def _make_contextual_api_call(self, step_name: str, conversation_messages: List[Dict],
                                 task_id: str, drawing_id: int) -> Dict[str, Any]:
        """进行带上下文的API调用"""
        try:
            from app.core.config import settings
            
            # 只使用最新的系统消息和用户消息
            messages = conversation_messages[-2:] if len(conversation_messages) >= 2 else conversation_messages
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content
            
            # 记录交互
            if self.interaction_logger:
                try:
                    self.interaction_logger.log_api_call(
                        session_id=f"{task_id}_{step_name}",
                        step_name=step_name,
                        request_data={"messages": messages},
                        response_data={"content": response_content},
                        task_id=task_id,
                        drawing_id=drawing_id
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 交互记录失败: {e}")
            
            # 解析响应
            try:
                parsed_response = json.loads(response_content)
                return {"success": True, "response": parsed_response}
            except json.JSONDecodeError:
                return {"success": True, "response": response_content, "raw": True}
            
        except Exception as e:
            logger.error(f"❌ {step_name} API调用失败: {e}")
            return {"error": str(e)}
    
    def _merge_multi_turn_results(self, results: List[Dict]) -> Dict[str, Any]:
        """合并多轮分析结果"""
        merged = {"success": True, "turns": len(results)}
        
        # 提取每轮的响应数据
        responses = []
        for i, result in enumerate(results):
            if result.get("success") and "response" in result:
                responses.append(result["response"])
        
        if responses:
            # 使用最后一轮的结果作为主要结果
            merged["qto_data"] = responses[-1]
            merged["all_responses"] = responses
        else:
            merged["error"] = "所有轮次都失败"
        
        return merged
    
    def _synthesize_qto_data(self, analysis_results: Dict) -> Dict[str, Any]:
        """综合分析结果生成QTO数据"""
        try:
            # 提取各步骤的数据
            drawing_info = analysis_results.get("step1_drawing_info", {}).get("response", {})
            component_ids = analysis_results.get("step2_component_ids", {}).get("response", {})
            component_counts = analysis_results.get("step3_component_counts", {}).get("response", {})
            positions = analysis_results.get("step4_positions", {}).get("response", {})
            attributes = analysis_results.get("step5_attributes", {}).get("response", {})
            
            # 构建综合QTO数据
            qto_data = {
                "drawing_info": drawing_info,
                "components": self._build_component_list(component_ids, component_counts, positions, attributes),
                "summary": self._generate_quantity_summary_from_analysis(analysis_results),
                "analysis_steps": {
                    "step1": "图纸信息提取",
                    "step2": "构件编号识别", 
                    "step3": "构件数量统计",
                    "step4": "位置信息提取",
                    "step5": "属性信息提取"
                }
            }
            
            return {"success": True, "qto_data": qto_data}
            
        except Exception as e:
            logger.error(f"❌ QTO数据综合失败: {e}")
            return {"error": str(e)}
    
    def _build_component_list(self, component_ids: Dict, component_counts: Dict, 
                            positions: Dict, attributes: Dict) -> List[Dict]:
        """构建构件清单"""
        components = []
        
        # 遍历识别的构件编号
        for comp_type, ids in component_ids.items():
            if isinstance(ids, list):
                for comp_id in ids:
                    component = {
                        "component_id": comp_id,
                        "component_type": self._determine_component_type(comp_id),
                        "count": component_counts.get(comp_id, 1),
                        "position": positions.get(comp_id, {}),
                        "dimensions": attributes.get(comp_id, {}),
                        "source": "5步分析法"
                    }
                    components.append(component)
        
        return components
    
    def _determine_component_type(self, component_id: str) -> str:
        """根据构件编号确定构件类型"""
        if component_id.startswith("KZ"):
            return "框架柱"
        elif component_id.startswith("L"):
            return "梁"
        elif component_id.startswith("B"):
            return "板"
        elif component_id.startswith("Q"):
            return "墙"
        else:
            return "其他构件"
    
    def _generate_quantity_summary_from_analysis(self, analysis_results: Dict) -> Dict[str, Any]:
        """从分析结果生成工程量汇总"""
        summary = {
            "total_components": 0,
            "component_types": {},
            "analysis_quality": "good"
        }
        
        try:
            component_counts = analysis_results.get("step3_component_counts", {}).get("response", {})
            
            for comp_type, count in component_counts.items():
                if isinstance(count, (int, float)):
                    summary["total_components"] += count
                    comp_category = self._determine_component_type(comp_type)
                    summary["component_types"][comp_category] = summary["component_types"].get(comp_category, 0) + count
        
        except Exception as e:
            logger.warning(f"⚠️ 汇总生成异常: {e}")
            summary["analysis_quality"] = "limited"
        
        return summary 