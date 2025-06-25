#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Analyzer Core - 重构后的AI分析器核心
负责协调各个专门的分析模块
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# 导入双重存储服务
from app.services.dual_storage_service import DualStorageService

# 导入OpenAI交互记录器
try:
    from app.services.openai_interaction_logger import OpenAIInteractionLogger
except ImportError:
    OpenAIInteractionLogger = None
    
# 导入OpenAI客户端和配置
try:
    from openai import OpenAI
    from app.core.config import settings
except ImportError:
    OpenAI = None
    settings = None

logger = logging.getLogger(__name__)

class AIAnalyzerCore:
    """
    AI分析器核心类
    协调各个专门的分析模块，提供统一的分析接口
    """
    
    def __init__(self):
        """初始化AI分析器核心"""
        self._initialize_openai_client()
        self._initialize_storage_service()
        self._initialize_interaction_logger()
        self._initialize_analysis_modules()
        
    def _initialize_openai_client(self):
        """初始化OpenAI客户端"""
        if not OpenAI or not settings or not settings.OPENAI_API_KEY:
            self.client = None
            logger.warning("⚠️ OpenAI或配置不可用，AI分析服务将处于禁用状态。")
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ AI Analyzer Core initialized successfully with OpenAI client.")
    
    def _initialize_storage_service(self):
        """初始化存储服务"""
        try:
            self.storage_service = DualStorageService()
            logger.info("✅ AIAnalyzerCore: DualStorageService initialized.")
        except Exception as e:
            self.storage_service = None
            logger.warning(f"⚠️ AIAnalyzerCore: DualStorageService failed to initialize: {e}")
    
    def _initialize_interaction_logger(self):
        """初始化交互记录器"""
        if OpenAIInteractionLogger and self.storage_service:
            try:
                self.interaction_logger = OpenAIInteractionLogger(storage_service=self.storage_service)
                logger.info("✅ OpenAIInteractionLogger 初始化成功")
            except Exception as e:
                logger.error(f"❌ OpenAIInteractionLogger初始化异常: {e}")
                self.interaction_logger = None
        else:
            logger.error("❌ OpenAIInteractionLogger未定义或DualStorageService未初始化")
            self.interaction_logger = None
    
    def _initialize_analysis_modules(self):
        """初始化各个分析模块"""
        # 延迟导入以避免循环依赖
        try:
            from .ai.mock_detector import MockDataDetector
            self.mock_detector = MockDataDetector()
        except ImportError:
            logger.warning("⚠️ MockDataDetector 导入失败，将使用简化版本")
            self.mock_detector = None
        
        # TODO: 添加其他分析模块的初始化
        # from .ai.prompt_builder import PromptBuilder
        # from .ai.vision_analyzer import VisionAnalyzer
        # from .ai.response_synthesizer import ResponseSynthesizer
        
        logger.info("✅ AI分析模块初始化完成")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None
    
    def generate_qto_from_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据OCR文本和表格数据，调用LLM生成结构化的工程量清单（QTO）
        
        Args:
            extracted_data: 从UnifiedOCREngine传来的、包含文本和表格的数据
            
        Returns:
            Dict[str, Any]: 大模型生成的结构化QTO数据
        """
        if not self.is_available():
            return {"error": "AI Analyzer Service is not available."}

        logger.info("🤖 Starting QTO generation with LLM...")

        try:
            # 1. 构建系统Prompt
            system_prompt = self._build_system_prompt()

            # 2. 构建用户Prompt  
            user_prompt = self._build_user_prompt(extracted_data)
            
            if not user_prompt:
                logger.warning("No data available to build a prompt. Aborting LLM call.")
                return {"error": "No content to analyze."}

            # 3. 调用OpenAI API
            logger.info(f"Sending request to OpenAI model: {settings.OPENAI_MODEL}")
            
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
            
            # 4. 解析结果
            qto_json_string = response.choices[0].message.content
            logger.info("✅ Successfully received response from LLM.")
            
            if not qto_json_string:
                logger.error("LLM returned empty response")
                return {"error": "Empty response from LLM"}
            
            try:
                qto_data = json.loads(qto_json_string)
                
                # 5. 模拟数据检测
                if self.mock_detector:
                    has_mock_data = self.mock_detector.check_for_mock_data_patterns(qto_data)
                    if has_mock_data:
                        logger.warning("🚨 检测到可能的模拟数据")
                
                return {"success": True, "qto_data": qto_data}
                
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from LLM response.")
                return {"error": "Invalid JSON response from LLM", "raw_response": qto_json_string}

        except Exception as e:
            logger.error(f"❌ An error occurred while calling OpenAI API: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词（简化版本）"""
        return """
        # 角色定义
        你是一名国家一级注册建造师和高级造价工程师，具有20年建筑工程量清单编制经验。
        
        # 核心任务
        分析建筑图纸OCR识别数据，按照国家工程量计算规范生成标准化的工程量清单（QTO）。
        
        # 重要要求
        1. 基于真实图纸数据进行分析，不要生成模拟数据
        2. 确保构件编号与图纸实际标注一致
        3. 尺寸和配筋信息必须来源于图纸识别结果
        4. 输出JSON格式的结构化数据
        
        # 输出格式
        返回包含project_info和components的JSON结构。
        """
    
    def _build_user_prompt(self, data: Dict[str, Any]) -> Optional[str]:
        """构建用户提示词（简化版本）"""
        try:
            prompt_parts = []
            
            # 添加OCR文本数据
            ocr_texts = data.get("ocr_texts", [])
            if ocr_texts:
                prompt_parts.append("## OCR识别的文本数据:")
                for text in ocr_texts[:20]:  # 限制前20个
                    prompt_parts.append(f"- {text}")
            
            # 添加表格数据
            tables = data.get("tables", [])
            if tables:
                prompt_parts.append("\n## 识别的表格数据:")
                for i, table in enumerate(tables[:3]):  # 限制前3个表格
                    prompt_parts.append(f"表格{i+1}: {table}")
            
            if not prompt_parts:
                return None
            
            prompt_parts.append("\n## 任务要求:")
            prompt_parts.append("请基于以上图纸数据，生成标准化的工程量清单JSON。")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"构建用户提示词失败: {e}")
            return None 