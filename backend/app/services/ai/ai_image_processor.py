#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI图像处理器组件
负责图像预处理、编码和Vision分析
"""
import logging
import base64
import os
from typing import Dict, Any, List, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)

class AIImageProcessor:
    """AI图像处理器"""
    
    def __init__(self, core_analyzer):
        """初始化图像处理器"""
        self.core_analyzer = core_analyzer
        
    def _prepare_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """
        准备图像数据，转换为OpenAI Vision API所需格式
        
        Args:
            image_paths: 图像文件路径列表
            
        Returns:
            List[Dict[str, Any]]: 处理后的图像数据列表
        """
        images_data = []
        
        for image_path in image_paths:
            try:
                if not os.path.exists(image_path):
                    logger.error(f"图像文件不存在: {image_path}")
                    continue
                    
                # 读取图像文件
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                
                # 压缩图像（如果需要）
                compressed_data = self._compress_image_if_needed(image_data)
                
                # 转换为base64编码
                base64_image = base64.b64encode(compressed_data).decode('utf-8')
                
                # 检测图像格式
                image_format = self._detect_image_format(image_path)
                
                images_data.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{base64_image}",
                        "detail": "high"  # 高详细度分析
                    }
                })
                
                logger.info(f"✅ 图像处理完成: {image_path}")
                
            except Exception as e:
                logger.error(f"❌ 图像处理失败 {image_path}: {e}")
                continue
        
        logger.info(f"📷 共处理 {len(images_data)} 张图像")
        return images_data

    def _compress_image_if_needed(self, image_data: bytes, max_size_mb: float = 20.0) -> bytes:
        """
        如果图像过大则压缩图像
        
        Args:
            image_data: 原始图像数据
            max_size_mb: 最大允许大小（MB）
            
        Returns:
            bytes: 压缩后的图像数据
        """
        image_size_mb = len(image_data) / (1024 * 1024)
        
        if image_size_mb <= max_size_mb:
            return image_data
        
        logger.info(f"🔄 图像大小 {image_size_mb:.2f}MB 超过限制，开始压缩...")
        
        try:
            # 使用PIL进行压缩
            image = Image.open(io.BytesIO(image_data))
            
            # 计算压缩比例
            compression_ratio = max_size_mb / image_size_mb
            new_width = int(image.width * compression_ratio ** 0.5)
            new_height = int(image.height * compression_ratio ** 0.5)
            
            # 调整图像大小
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存压缩后的图像
            compressed_buffer = io.BytesIO()
            if image.format:
                resized_image.save(compressed_buffer, format=image.format, quality=85)
            else:
                resized_image.save(compressed_buffer, format='JPEG', quality=85)
            
            compressed_data = compressed_buffer.getvalue()
            compressed_size_mb = len(compressed_data) / (1024 * 1024)
            
            logger.info(f"✅ 图像压缩完成: {image_size_mb:.2f}MB → {compressed_size_mb:.2f}MB")
            return compressed_data
            
        except Exception as e:
            logger.error(f"❌ 图像压缩失败: {e}")
            return image_data

    def _detect_image_format(self, image_path: str) -> str:
        """检测图像格式"""
        extension = os.path.splitext(image_path)[1].lower()
        format_map = {
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.png': 'png',
            '.webp': 'webp',
            '.gif': 'gif'
        }
        return format_map.get(extension, 'jpeg')

    def generate_qto_from_local_images(self, 
                                     image_paths: List[str], 
                                     context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        基于本地图像路径生成工程量清单
        
        Args:
            image_paths: 本地图像文件路径列表
            context_data: 上下文数据
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self.core_analyzer.is_available():
            return {"error": "AI Analyzer Service is not available."}
        
        if not image_paths:
            return {"error": "No image paths provided."}
        
        # 准备图像数据
        images_data = self._prepare_images(image_paths)
        if not images_data:
            return {"error": "No valid images could be processed."}
        
        # 调用图像分析
        return self.generate_qto_from_encoded_images(images_data, context_data)

    def generate_qto_from_encoded_images(self, 
                                       images_data: List[Dict[str, Any]], 
                                       context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        基于编码图像数据生成工程量清单
        
        Args:
            images_data: 编码后的图像数据列表
            context_data: 上下文数据
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self.core_analyzer.is_available():
            return {"error": "AI Analyzer Service is not available."}
        
        logger.info("🤖 开始Vision图像分析...")
        
        try:
            # 导入提示词构建器
            from .ai_prompt_builder import PromptBuilder
            prompt_builder = PromptBuilder()
            
            # 构建增强的系统提示词
            system_prompt = prompt_builder.build_enhanced_system_prompt()
            
            # 构建用户消息
            user_message = self._build_vision_user_message(images_data, context_data)
            
            # 调用OpenAI Vision API
            from app.core.config import settings
            response = self.core_analyzer.client.chat.completions.create(
                model=settings.OPENAI_VISION_MODEL or settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            response_text = response.choices[0].message.content
            
            if not response_text:
                logger.error("Vision API返回空响应")
                return {"error": "Empty response from Vision API"}
            
            try:
                import json
                qto_data = json.loads(response_text)
                
                # 验证结果真实性
                authenticity_errors = self.core_analyzer._validate_response_authenticity(qto_data)
                has_mock_patterns = self.core_analyzer._check_for_mock_data_patterns(qto_data)
                
                result = {
                    "success": True,
                    "qto_data": qto_data,
                    "analysis_metadata": {
                        "source": "vision_analysis",
                        "image_count": len(images_data),
                        "authenticity_check": {
                            "errors": authenticity_errors,
                            "has_mock_patterns": has_mock_patterns
                        }
                    }
                }
                
                if authenticity_errors or has_mock_patterns:
                    result["warnings"] = {
                        "authenticity_issues": authenticity_errors,
                        "possible_mock_data": has_mock_patterns
                    }
                
                logger.info("✅ Vision图像分析完成")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Vision API响应JSON解析失败: {e}")
                return {
                    "error": "Invalid JSON response from Vision API",
                    "raw_response": response_text
                }
        
        except Exception as e:
            logger.error(f"❌ Vision图像分析异常: {e}", exc_info=True)
            return {"error": str(e)}

    def _build_vision_user_message(self, 
                                 images_data: List[Dict[str, Any]], 
                                 context_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """构建Vision API的用户消息"""
        
        # 基础文本提示
        text_prompt = """
        # 建筑施工图纸工程量分析任务

        ## 任务说明
        请仔细分析提供的建筑施工图纸，基于图纸实际可见内容生成准确的工程量清单。

        ## 关键要求
        1. **真实性第一**：只分析图纸上实际可见的内容，严禁编造数据
        2. **精确识别**：准确读取构件编号、尺寸标注、配筋信息
        3. **规范计算**：按照国家工程量计算规范进行计算
        4. **质量控制**：标注信息缺失或不清晰的部分

        ## 分析重点
        - 图框信息：项目名称、图纸编号、设计单位等
        - 构件信息：编号、类型、尺寸、位置
        - 配筋信息：主筋、箍筋规格和布置
        - 混凝土等级：不同构件的强度等级

        请严格按照JSON格式要求输出分析结果。
        """
        
        # 构建消息内容
        message_content = [
            {"type": "text", "text": text_prompt}
        ]
        
        # 添加图像内容
        for image_data in images_data:
            message_content.append(image_data)
        
        # 添加上下文信息
        if context_data:
            context_text = self._build_context_text(context_data)
            if context_text:
                message_content.append({
                    "type": "text", 
                    "text": f"\n## 上下文信息\n{context_text}"
                })
        
        return message_content

    def _build_context_text(self, context_data: Dict[str, Any]) -> str:
        """构建上下文文本"""
        context_parts = []
        
        if context_data.get('drawing_id'):
            context_parts.append(f"- 图纸ID: {context_data['drawing_id']}")
        
        if context_data.get('batch_id'):
            context_parts.append(f"- 批次ID: {context_data['batch_id']}")
        
        if context_data.get('slice_info'):
            slice_info = context_data['slice_info']
            context_parts.append(f"- 切片信息: {slice_info.get('total_slices', 0)} 个切片")
        
        if context_data.get('processing_stage'):
            context_parts.append(f"- 处理阶段: {context_data['processing_stage']}")
        
        return "\n".join(context_parts) if context_parts else "" 