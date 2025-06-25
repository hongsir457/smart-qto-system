#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析器核心 - 整合所有AI分析功能的核心协调器
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional

# 导入子模块
from .mock_data_detector import MockDataDetector
from .prompt_builder import PromptBuilder
from .vision_analyzer import VisionAnalyzer
from .response_processor import ResponseProcessor
from .context_manager import ContextManager

logger = logging.getLogger(__name__)

class AIAnalyzerCore:
    """
    AI分析器核心类 - 协调所有分析功能
    """
    
    def __init__(self, openai_client=None, storage_service=None, interaction_logger=None):
        """初始化AI分析器核心"""
        self.client = openai_client
        self.storage_service = storage_service
        self.interaction_logger = interaction_logger
        
        # 初始化子模块
        self.mock_detector = MockDataDetector()
        self.prompt_builder = PromptBuilder()
        self.context_manager = ContextManager()
        self.response_processor = ResponseProcessor(self.mock_detector)
        self.vision_analyzer = VisionAnalyzer(
            self.client, 
            self.interaction_logger, 
            self.prompt_builder
        )
        
        logger.info("✅ AIAnalyzerCore initialized with all sub-modules")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None
    
    def generate_qto_from_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """根据OCR文本和表格数据生成QTO"""
        if not self.is_available():
            return {"error": "AI Analyzer Service is not available."}

        logger.info("🤖 开始基于OCR数据的QTO生成...")

        try:
            # 1. 构建提示词
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(extracted_data)
            
            if not user_prompt:
                logger.warning("无法构建用户提示词，中止LLM调用")
                return {"error": "No content to analyze."}

            # 2. 调用OpenAI API
            response = self._make_api_call(system_prompt, user_prompt)
            if "error" in response:
                return response
            
            # 3. 处理响应
            result = self.response_processor.process_qto_response(response["content"])
            
            logger.info("✅ 基于OCR数据的QTO生成完成")
            return result

        except Exception as e:
            logger.error(f"❌ QTO生成异常: {e}")
            return {"error": str(e)}
    
    def generate_qto_from_local_images(self, image_paths: List[str], 
                                      task_id: str = None, drawing_id: int = None) -> Dict[str, Any]:
        """从本地图像生成QTO"""
        if not self.is_available():
            return {"error": "AI Analyzer Service is not available."}

        logger.info(f"🔍 开始基于图像的QTO生成，图像数量: {len(image_paths)}")

        try:
            # 1. 准备图像数据
            encoded_images = self.vision_analyzer.prepare_images(image_paths)
            if not encoded_images:
                return {"error": "No valid images to analyze"}
            
            # 2. 执行多轮分析
            result = self.vision_analyzer.execute_multi_turn_analysis(
                encoded_images, task_id, drawing_id
            )
            
            return result

        except Exception as e:
            logger.error(f"❌ 图像QTO生成异常: {e}")
            return {"error": str(e)}
    
    def generate_qto_from_encoded_images(self, encoded_images: List[Dict],
                                       task_id: str = None, drawing_id: int = None,
                                       slice_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """从编码图像生成QTO（支持切片元数据）"""
        if not self.is_available():
            return {"error": "AI Analyzer Service is not available."}

        logger.info(f"🔍 开始基于编码图像的QTO生成，图像数量: {len(encoded_images)}")

        try:
            # 1. 执行多轮分析
            result = self.vision_analyzer.execute_multi_turn_analysis(
                encoded_images, task_id, drawing_id
            )
            
            # 2. 如果有切片元数据，融合到结果中
            if slice_metadata and result.get("success"):
                result = self._integrate_slice_metadata(result, slice_metadata)
            
            return result

        except Exception as e:
            logger.error(f"❌ 编码图像QTO生成异常: {e}")
            return {"error": str(e)}
    
    def generate_qto_from_local_images_v2(self, image_paths: List[str], 
                                         task_id: str = None, drawing_id: int = None) -> Dict[str, Any]:
        """V2版本：使用5步上下文分析法"""
        if not self.is_available():
            return {"error": "AI Analyzer Service is not available."}

        logger.info(f"🔍 开始V2五步分析法，图像数量: {len(image_paths)}")

        try:
            # 1. 准备图像数据
            encoded_images = self.vision_analyzer.prepare_images(image_paths)
            if not encoded_images:
                return {"error": "No valid images to analyze"}
            
            # 2. 执行五步上下文分析
            result = self.vision_analyzer.execute_multi_turn_analysis_with_context(
                encoded_images, task_id, drawing_id
            )
            
            return result

        except Exception as e:
            logger.error(f"❌ V2五步分析异常: {e}")
            return {"error": str(e)}
    
    async def analyze_text_async(self, prompt: str, session_id: str = None,
                               context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """异步文本分析"""
        if not self.is_available():
            return {"error": "AI Analyzer Service is not available."}

        try:
            # 1. 启动会话（如果提供了session_id）
            if session_id:
                self.context_manager.start_session(session_id, context_data)
            
            # 2. 构建提示词
            if context_data:
                enhanced_prompt = f"{prompt}\n\n上下文信息:\n{context_data}"
            else:
                enhanced_prompt = prompt
            
            # 3. 异步API调用
            response = await self._make_async_api_call(enhanced_prompt)
            
            # 4. 处理响应
            if "error" in response:
                return response
            
            result = {
                "success": True,
                "response": response["content"],
                "session_id": session_id
            }
            
            # 5. 更新会话状态
            if session_id:
                self.context_manager.add_message(session_id, "user", prompt)
                self.context_manager.add_message(session_id, "assistant", response["content"])
            
            return result

        except Exception as e:
            logger.error(f"❌ 异步文本分析异常: {e}")
            return {"error": str(e)}
    
    def _make_api_call(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """执行标准API调用"""
        try:
            from app.core.config import settings
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            return {"success": True, "content": response.choices[0].message.content}
            
        except Exception as e:
            logger.error(f"❌ API调用失败: {e}")
            return {"error": str(e)}
    
    async def _make_async_api_call(self, prompt: str) -> Dict[str, Any]:
        """执行异步API调用"""
        try:
            from app.core.config import settings
            
            # 使用异步客户端（如果可用）
            if hasattr(self.client, 'achat'):
                response = await self.client.achat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=settings.OPENAI_TEMPERATURE,
                    max_tokens=2048  # 增加max_tokens确保输出完整
                )
            else:
                # 回退到同步调用
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=settings.OPENAI_TEMPERATURE,
                    max_tokens=2048  # 增加max_tokens确保输出完整
                )
            
            finish_reason = response.choices[0].finish_reason
            logger.info(f"✅ 异步API调用完成，finish_reason: {finish_reason}")
            
            return {
                "success": True, 
                "content": response.choices[0].message.content,
                "finish_reason": finish_reason
            }
            
        except Exception as e:
            logger.error(f"❌ 异步API调用失败: {e}")
            return {"error": str(e)}
    
    def _integrate_slice_metadata(self, result: Dict, slice_metadata: Dict) -> Dict:
        """将切片元数据集成到分析结果中"""
        try:
            if "qto_data" in result:
                qto_data = result["qto_data"]
                
                # 添加切片信息到元数据
                if "_metadata" not in qto_data:
                    qto_data["_metadata"] = {}
                
                qto_data["_metadata"]["slice_info"] = slice_metadata
                qto_data["_metadata"]["analysis_type"] = "slice_based"
                
                # 如果有坐标信息，尝试还原构件位置
                if "grid_info" in slice_metadata:
                    qto_data = self._restore_component_coordinates(qto_data, slice_metadata)
                
                result["qto_data"] = qto_data
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 切片元数据集成失败: {e}")
            return result
    
    def _restore_component_coordinates(self, qto_data: Dict, slice_metadata: Dict) -> Dict:
        """还原构件在原图中的坐标"""
        try:
            if "components" not in qto_data:
                return qto_data
            
            grid_info = slice_metadata.get("grid_info", {})
            slice_position = slice_metadata.get("slice_position", {})
            
            for component in qto_data["components"]:
                if "position" in component and isinstance(component["position"], dict):
                    # 基于切片位置还原全局坐标
                    local_x = component["position"].get("x", 0)
                    local_y = component["position"].get("y", 0)
                    
                    global_x = slice_position.get("x", 0) + local_x
                    global_y = slice_position.get("y", 0) + local_y
                    
                    component["position"]["global_x"] = global_x
                    component["position"]["global_y"] = global_y
                    component["position"]["slice_id"] = slice_metadata.get("slice_id")
            
            return qto_data
            
        except Exception as e:
            logger.warning(f"⚠️ 坐标还原失败: {e}")
            return qto_data
    
    # 保持向后兼容的方法
    def start_session(self, *args, **kwargs):
        """向后兼容的会话启动方法"""
        return self.context_manager.start_session(*args, **kwargs)
    
    def log_api_call(self, *args, **kwargs):
        """向后兼容的API调用记录方法"""
        if self.interaction_logger:
            return self.interaction_logger.log_api_call(*args, **kwargs)
    
    def end_session_and_save(self, *args, **kwargs):
        """向后兼容的会话结束方法"""
        if self.interaction_logger:
            return self.interaction_logger.end_session_and_save(*args, **kwargs) 