#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析器核心组件
负责基础配置、客户端初始化和核心分析功能
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# 导入OpenAI客户端和配置
try:
    from openai import OpenAI
    from app.core.config import settings
except ImportError:
    OpenAI = None
    settings = None

logger = logging.getLogger(__name__)

class AIAnalyzerCore:
    """AI分析器核心类"""
    
    def __init__(self):
        """初始化AI分析服务客户端"""
        if not OpenAI or not settings or not settings.OPENAI_API_KEY:
            self.client = None
            logger.warning("⚠️ OpenAI或配置不可用，AI分析服务将处于禁用状态。")
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ AI Analyzer Core initialized successfully with OpenAI client.")
        
        # 简化交互记录器初始化
        self.interaction_logger = None

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None

    async def analyze_text_async(self, 
                               prompt: str, 
                               session_id: str = None,
                               context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        异步文本分析方法，支持AI交互记录保存
        
        Args:
            prompt: 分析提示词
            session_id: 会话ID
            context_data: 上下文数据
            
        Returns:
            分析结果字典
        """
        if not self.is_available():
            return {"success": False, "error": "AI Analyzer Service is not available."}
        
        start_time = time.time()
        
        try:
            logger.info(f"🤖 开始AI文本分析 (会话: {session_id})")
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位专业的建筑工程造价师，请根据要求进行精确分析。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS
            )
            
            # 获取响应文本
            response_text = response.choices[0].message.content
            usage_info = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            # 构建结果
            result = {
                "success": True,
                "response": response_text,
                "usage": usage_info,
                "model": settings.OPENAI_MODEL,
                "session_id": session_id,
                "processing_time": time.time() - start_time
            }
            
            # 记录AI交互信息（简化版）
            if context_data and session_id:
                try:
                    drawing_id = context_data.get("drawing_id", "unknown")
                    logger.info(f"🤖 AI交互记录: session={session_id}, drawing={drawing_id}, tokens={usage_info.get('total_tokens', 0)}")
                except Exception as log_exc:
                    logger.debug(f"交互记录日志异常: {log_exc}")
            
            logger.info(f"✅ AI文本分析完成: {len(response_text)} 个字符")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI文本分析异常: {e}", exc_info=True)
            return {
                "success": False, 
                "error": str(e),
                "session_id": session_id,
                "processing_time": time.time() - start_time
            }

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

        # 导入提示词构建器
        from .ai_prompt_builder import PromptBuilder
        prompt_builder = PromptBuilder()

        # 1. 构建系统Prompt
        system_prompt = prompt_builder.build_system_prompt()

        # 2. 构建用户Prompt
        user_prompt = prompt_builder.build_user_prompt(extracted_data)
        
        if not user_prompt:
            logger.warning("No data available to build a prompt. Aborting LLM call.")
            return {"error": "No content to analyze."}

        # 3. 调用OpenAI API
        try:
            logger.info(f"Sending request to OpenAI model: {settings.OPENAI_MODEL}")
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}  # 要求返回JSON对象
            )
            
            # 4. 解析结果
            qto_json_string = response.choices[0].message.content
            logger.info("✅ Successfully received response from LLM.")
            
            if not qto_json_string:
                logger.error("LLM returned empty response")
                return {"error": "Empty response from LLM"}
            
            try:
                qto_data = json.loads(qto_json_string)
                return {"success": True, "qto_data": qto_data}
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from LLM response.")
                return {"error": "Invalid JSON response from LLM", "raw_response": qto_json_string}

        except Exception as e:
            logger.error(f"❌ An error occurred while calling OpenAI API: {e}", exc_info=True)
            return {"error": str(e)}

    def _validate_response_authenticity(self, qto_data: Dict) -> List[str]:
        """验证响应内容的真伪"""
        errors = []
        
        # 检查项目信息
        drawing_info = qto_data.get("drawing_info", {})
        project_name = drawing_info.get("project_name", "")
        
        # 检查项目名称
        if not project_name:
            errors.append("项目名称缺失")
        
        # 检查图纸比例
        scale = drawing_info.get("scale", "")
        if not scale:
            errors.append("图纸比例缺失")
        
        # 检查构件数量
        components = qto_data.get("components", [])
        if not components:
            errors.append("构件数量为零")
        
        # 检查构件编号
        for comp in components:
            component_id = comp.get("component_id", "")
            if not component_id:
                errors.append(f"构件编号缺失: {comp}")
        
        return errors

    def _check_for_mock_data_patterns(self, qto_data: Dict) -> bool:
        """检查QTO数据是否包含模拟数据的模式"""
        try:
            mock_indicators_found = []
            
            # 1. 检查项目信息中的模拟数据标识
            drawing_info = qto_data.get("drawing_info", {})
            project_name = drawing_info.get("project_name", "")
            title = drawing_info.get("title", "")
            
            project_mock_indicators = [
                "某建筑工程项目", "某建筑结构施工图", "某住宅楼", "某办公楼",
                "示例项目", "测试项目", "演示项目", "样例工程",
                "XX项目", "XXX工程", "demo", "example", "test",
                "某建筑", "某项目", "某工程", "某结构"
            ]
            
            for indicator in project_mock_indicators:
                if indicator.lower() in project_name.lower() or indicator.lower() in title.lower():
                    mock_indicators_found.append(f"项目名称包含模拟标识: '{indicator}'")
                    logger.warning(f"🚨 发现模拟数据标识: '{indicator}' in {project_name or title}")
            
            # 2. 检查构件编号的规律性模式
            components = qto_data.get("components", [])
            if len(components) >= 3:
                component_ids = [comp.get("component_id", "") for comp in components]
                
                # 检查KZ-1, KZ-2, KZ-3类型的连续编号
                kz_ids = [comp_id for comp_id in component_ids if comp_id.startswith("KZ-")]
                if len(kz_ids) >= 3:
                    kz_pattern = all(
                        comp_id == f"KZ-{i+1}" for i, comp_id in enumerate(kz_ids)
                    )
                    if kz_pattern:
                        mock_indicators_found.append("构件编号呈现规律性连续模式(KZ-1,KZ-2,KZ-3...)")
                        logger.warning("🚨 发现规律性构件编号模式")
            
            # 综合评估
            if mock_indicators_found:
                logger.warning(f"🚨 发现 {len(mock_indicators_found)} 个模拟数据特征:")
                for indicator in mock_indicators_found:
                    logger.warning(f"   - {indicator}")
                return True
            else:
                logger.info("✅ 数据检查通过，未发现明显的模拟数据特征")
                return False
            
        except Exception as e:
            logger.error(f"检查模拟数据模式时出错: {e}")
            return False 