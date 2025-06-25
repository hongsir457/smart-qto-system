#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Vision切片分析器
集成智能切片和OpenAI Vision API调用
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import openai
from dataclasses import asdict

from app.core.config import settings
from app.services.intelligent_image_slicer import (
    IntelligentImageSlicer, 
    SliceInfo, 
    SliceAnalysisResult
)
from app.services.fallback_strategy import fallback_strategy, FallbackLevel

logger = logging.getLogger(__name__)

class OpenAIVisionSlicer:
    """OpenAI Vision切片分析器"""
    
    def __init__(self):
        """初始化Vision切片分析器"""
        self.slicer = IntelligentImageSlicer()
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-vision-preview"  # 支持Vision的模型
        self.max_retries = 3
        self.retry_delay = 2
        
    async def analyze_image_with_slicing(self, image_path: str, task_id: str,
                                       analysis_prompt: str = None) -> Dict[str, Any]:
        """
        使用智能切片进行图像分析（带降级策略）
        
        Args:
            image_path: 图像文件路径
            task_id: 任务ID
            analysis_prompt: 分析提示词
            
        Returns:
            完整的分析结果
        """
        logger.info(f"开始Vision切片分析（带降级策略）- 任务ID: {task_id}")
        
        # 准备降级函数
        async def primary_slicing_func(**kwargs):
            return await self._execute_slicing_analysis(**kwargs)
        
        async def direct_analysis_func(**kwargs):
            return await self.analyze_full_image_direct(
                kwargs['image_path'], 
                kwargs['task_id'], 
                kwargs.get('analysis_prompt')
            )
        
        async def ocr_fallback_func(**kwargs):
            return await self._execute_ocr_fallback(**kwargs)
        
        # 使用降级策略执行分析
        fallback_result = await fallback_strategy.execute_with_fallback(
            primary_func=primary_slicing_func,
            fallback_funcs=[direct_analysis_func, ocr_fallback_func],
            task_id=task_id,
            image_path=image_path,
            analysis_prompt=analysis_prompt or self._get_default_analysis_prompt()
        )
        
        # 构建最终响应
        final_result = {
            'task_id': task_id,
            'analysis_type': 'vision_slicing_with_fallback',
            'fallback_info': {
                'level': fallback_result.level.value,
                'success': fallback_result.success,
                'processing_time': fallback_result.processing_time,
                'fallback_reason': fallback_result.fallback_reason
            },
            'data': fallback_result.data
        }
        
        if fallback_result.success:
            logger.info(f"Vision分析成功 - 任务ID: {task_id}, 级别: {fallback_result.level.value}")
        else:
            logger.error(f"Vision分析失败 - 任务ID: {task_id}, 错误: {fallback_result.error_message}")
            final_result['error'] = fallback_result.error_message
        
        return final_result
    
    async def _execute_slicing_analysis(self, image_path: str, task_id: str,
                                      analysis_prompt: str, **kwargs) -> Dict[str, Any]:
        """
        执行原始的切片分析逻辑
        
        Args:
            image_path: 图像文件路径
            task_id: 任务ID
            analysis_prompt: 分析提示词
            
        Returns:
            切片分析结果
        """
        try:
            # 1. 图像切片处理
            slice_result = await self.slicer.process_image_with_slicing(image_path, task_id)
            
            if not slice_result['ready_for_analysis']:
                raise Exception("图像切片处理失败")
            
            # 2. 获取切片信息
            slices_info = slice_result['slices_info']
            original_size = slice_result['original_size']
            
            logger.info(f"准备分析 {len(slices_info)} 个切片")
            
            # 3. 并行分析所有切片
            slice_analysis_tasks = []
            
            for slice_info in slices_info:
                task = self._analyze_single_slice(
                    slice_info, 
                    task_id, 
                    analysis_prompt or self._get_default_analysis_prompt()
                )
                slice_analysis_tasks.append(task)
            
            # 执行并行分析
            slice_results = await asyncio.gather(*slice_analysis_tasks, return_exceptions=True)
            
            # 4. 处理分析结果
            valid_results = []
            failed_slices = []
            
            for i, result in enumerate(slice_results):
                if isinstance(result, Exception):
                    logger.error(f"切片 {slices_info[i]['slice_id']} 分析失败: {result}")
                    failed_slices.append(slices_info[i]['slice_id'])
                else:
                    valid_results.append(result)
            
            if not valid_results:
                raise Exception("所有切片分析都失败了")
            
            # 5. 合并分析结果
            slice_metadata = {
                'slice_info': [
                    {
                        'slice_id': info['slice_id'],
                        'position': info['position'],
                        'size': info['size'],
                        'overlap': (0, 0, 0, 0)  # 从切片器获取实际重叠信息
                    }
                    for info in slices_info
                ]
            }
            
            merged_result = self.slicer.merge_analysis_results(
                valid_results, original_size, slice_metadata
            )
            
            # 6. 保存结果到Sealos
            result_url = await self.slicer.save_merged_result_to_sealos(merged_result, task_id)
            
            # 7. 构建最终响应
            final_result = {
                'task_id': task_id,
                'analysis_type': 'vision_slicing',
                'original_image': {
                    'path': image_path,
                    'size': original_size
                },
                'slicing_info': {
                    'total_slices': len(slices_info),
                    'successful_slices': len(valid_results),
                    'failed_slices': failed_slices,
                    'slice_urls': slice_result['slice_urls']
                },
                'analysis_result': merged_result,
                'result_url': result_url,
                'processing_summary': {
                    'total_components': len(merged_result.get('components', [])),
                    'avg_confidence': merged_result.get('statistics', {}).get('avg_confidence', 0),
                    'coverage_ratio': merged_result.get('quality_metrics', {}).get('coverage_ratio', 0),
                    'success_rate': len(valid_results) / len(slices_info) if slices_info else 0
                }
            }
            
            logger.info(f"Vision切片分析完成 - 识别到 {len(merged_result.get('components', []))} 个构件")
            return final_result
            
        except Exception as e:
            logger.error(f"Vision切片分析失败: {e}")
            raise
    
    async def _analyze_single_slice(self, slice_info: Dict[str, Any], 
                                  task_id: str, analysis_prompt: str) -> SliceAnalysisResult:
        """
        分析单个切片
        
        Args:
            slice_info: 切片信息
            task_id: 任务ID
            analysis_prompt: 分析提示词
            
        Returns:
            切片分析结果
        """
        slice_id = slice_info['slice_id']
        logger.debug(f"开始分析切片: {slice_id}")
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # 构建消息
                messages = [
                    {
                        "role": "system",
                        "content": analysis_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"请分析这个图纸切片（切片ID: {slice_id}，位置: {slice_info['position']}，尺寸: {slice_info['size']}）中的建筑构件。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{slice_info.get('base64_data', '')}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ]
                
                # 调用OpenAI API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.1
                )
                
                # 解析响应
                analysis_text = response.choices[0].message.content
                
                # 解析分析结果
                parsed_result = self._parse_analysis_result(analysis_text, slice_id)
                
                processing_time = time.time() - start_time
                
                result = SliceAnalysisResult(
                    slice_id=slice_id,
                    analysis_result=parsed_result,
                    components=parsed_result.get('components', []),
                    confidence_score=parsed_result.get('confidence_score', 0.8),
                    processing_time=processing_time
                )
                
                logger.debug(f"切片 {slice_id} 分析成功，耗时 {processing_time:.2f}s")
                return result
                
            except Exception as e:
                logger.warning(f"切片 {slice_id} 分析失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e
    
    def _parse_analysis_result(self, analysis_text: str, slice_id: str) -> Dict[str, Any]:
        """
        解析OpenAI分析结果
        
        Args:
            analysis_text: 分析文本
            slice_id: 切片ID
            
        Returns:
            解析后的结构化结果
        """
        try:
            # 尝试从文本中提取JSON
            import re
            import json
            
            # 查找JSON块
            json_pattern = r'```json\s*(.*?)\s*```'
            json_match = re.search(json_pattern, analysis_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                parsed_data = json.loads(json_str)
                
                # 验证和标准化数据
                return self._standardize_analysis_result(parsed_data, slice_id)
            
            # 如果没有找到JSON，尝试简单解析
            return self._simple_parse_analysis(analysis_text, slice_id)
            
        except Exception as e:
            logger.warning(f"解析分析结果失败: {e}")
            return self._create_fallback_result(analysis_text, slice_id)
    
    def _standardize_analysis_result(self, data: Dict[str, Any], slice_id: str) -> Dict[str, Any]:
        """标准化分析结果格式"""
        
        # 确保必要字段存在
        standardized = {
            'slice_id': slice_id,
            'components': data.get('components', []),
            'confidence_score': data.get('confidence_score', 0.8),
            'analysis_summary': data.get('summary', ''),
            'detected_elements': data.get('detected_elements', []),
            'quality_assessment': data.get('quality', {}),
            'raw_response': data
        }
        
        # 标准化构件信息
        components = []
        for comp in standardized['components']:
            standardized_comp = {
                'id': comp.get('id', f"{slice_id}_comp_{len(components)}"),
                'type': comp.get('type', 'unknown'),
                'name': comp.get('name', ''),
                'bbox': comp.get('bbox', [0, 0, 100, 100]),
                'center': comp.get('center', [50, 50]),
                'confidence': comp.get('confidence', 0.8),
                'properties': comp.get('properties', {}),
                'dimensions': comp.get('dimensions', {}),
                'materials': comp.get('materials', []),
                'slice_source': slice_id
            }
            components.append(standardized_comp)
        
        standardized['components'] = components
        return standardized
    
    def _simple_parse_analysis(self, text: str, slice_id: str) -> Dict[str, Any]:
        """简单文本解析（备选方案）"""
        
        # 基于关键词识别构件
        component_keywords = {
            '柱': 'column',
            '梁': 'beam', 
            '板': 'slab',
            '墙': 'wall',
            '基础': 'foundation',
            '楼梯': 'stair'
        }
        
        detected_components = []
        
        for keyword, comp_type in component_keywords.items():
            if keyword in text:
                # 简单构件信息
                component = {
                    'id': f"{slice_id}_{comp_type}",
                    'type': comp_type,
                    'name': keyword,
                    'bbox': [0, 0, 100, 100],  # 默认边界框
                    'confidence': 0.6,  # 较低置信度
                    'properties': {'detection_method': 'keyword'},
                    'slice_source': slice_id
                }
                detected_components.append(component)
        
        return {
            'slice_id': slice_id,
            'components': detected_components,
            'confidence_score': 0.6,
            'analysis_summary': text[:200] + '...' if len(text) > 200 else text,
            'detection_method': 'simple_parse'
        }
    
    def _create_fallback_result(self, text: str, slice_id: str) -> Dict[str, Any]:
        """创建备选结果（解析失败时）"""
        
        return {
            'slice_id': slice_id,
            'components': [],
            'confidence_score': 0.3,
            'analysis_summary': '分析结果解析失败',
            'error': '无法解析OpenAI响应',
            'raw_text': text,
            'detection_method': 'fallback'
        }
    
    def _get_default_analysis_prompt(self) -> str:
        """获取默认分析提示词"""
        
        return """你是一个专业的建筑图纸分析专家。请分析提供的建筑图纸切片，识别其中的建筑构件。

请按照以下JSON格式返回分析结果：

```json
{
    "components": [
        {
            "id": "构件唯一标识",
            "type": "构件类型(column/beam/slab/wall/foundation/stair等)",
            "name": "构件名称",
            "bbox": [x1, y1, x2, y2],
            "center": [x, y],
            "confidence": 0.95,
            "properties": {
                "material": "材料",
                "size": "尺寸信息",
                "annotation": "标注信息"
            },
            "dimensions": {
                "length": "长度",
                "width": "宽度", 
                "height": "高度"
            }
        }
    ],
    "confidence_score": 0.92,
    "summary": "分析摘要",
    "detected_elements": ["检测到的元素列表"],
    "quality": {
        "image_clarity": "图像清晰度评估",
        "annotation_completeness": "标注完整性"
    }
}
```

重点关注：
1. 准确识别构件类型和位置
2. 提取尺寸和材料信息
3. 识别图纸标注和文字
4. 评估识别置信度
5. 注意这是图纸的一个切片，可能包含部分构件

请确保返回的坐标是相对于当前切片的像素坐标。"""
    
    async def analyze_full_image_direct(self, image_path: str, task_id: str,
                                      analysis_prompt: str = None) -> Dict[str, Any]:
        """
        直接分析完整图像（不切片，用于对比）
        
        Args:
            image_path: 图像文件路径
            task_id: 任务ID
            analysis_prompt: 分析提示词
            
        Returns:
            分析结果
        """
        logger.info(f"开始直接Vision分析 - 任务ID: {task_id}")
        
        try:
            from PIL import Image
            import base64
            import io
            
            # 加载并编码图像
            image = Image.open(image_path)
            
            # 如果图像太大，先压缩到OpenAI限制内
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"图像已压缩到: {new_size}")
            
            # 转换为base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', quality=95)
            base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": analysis_prompt or self._get_default_analysis_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"请分析这张完整的建筑图纸（任务ID: {task_id}）。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_data}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            # 调用OpenAI API
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=3000,
                temperature=0.1
            )
            
            processing_time = time.time() - start_time
            
            # 解析响应
            analysis_text = response.choices[0].message.content
            parsed_result = self._parse_analysis_result(analysis_text, f"{task_id}_full")
            
            # 构建结果
            result = {
                'task_id': task_id,
                'analysis_type': 'vision_direct',
                'original_image': {
                    'path': image_path,
                    'size': image.size
                },
                'analysis_result': parsed_result,
                'processing_time': processing_time,
                'compression_applied': max(image.size) > max_size,
                'final_resolution': image.size
            }
            
            logger.info(f"直接Vision分析完成，耗时 {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"直接Vision分析失败: {e}")
            raise
    
    async def _execute_ocr_fallback(self, image_path: str, task_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行OCR降级分析（使用智能切片OCR）
        
        Args:
            image_path: 图像文件路径
            task_id: 任务ID
            
        Returns:
            OCR分析结果
        """
        logger.info(f"执行OCR降级分析（智能切片）- 任务ID: {task_id}")
        
        try:
            # 导入增强版OCR服务
            from app.services.ocr.paddle_ocr_service import PaddleOCRService
            
            # 初始化OCR服务
            ocr_service = PaddleOCRService()
            
            # 执行OCR识别（自动判断是否使用切片）
            ocr_result = await ocr_service.process_image_async(
                image_path=image_path,
                use_slicing=True  # 在降级模式下强制使用切片以获得最佳效果
            )
            
            # 获取处理方法信息
            processing_method = ocr_result.get('processing_method', 'unknown')
            slicing_info = ocr_result.get('slicing_info', {})
            
            # 转换为标准格式
            standardized_result = {
                'task_id': task_id,
                'analysis_type': 'ocr_fallback_with_slicing',
                'original_image': {
                    'path': image_path
                },
                'ocr_result': ocr_result,
                'texts': ocr_result.get('texts', []),
                'text_regions': ocr_result.get('text_regions', []),
                'statistics': {
                    'total_texts': len(ocr_result.get('texts', [])),
                    'total_text_regions': ocr_result.get('statistics', {}).get('total_regions', 0),
                    'confidence_avg': ocr_result.get('statistics', {}).get('avg_confidence', 0.8),
                    'processing_time': ocr_result.get('statistics', {}).get('processing_time', 0)
                },
                'processing_info': {
                    'method': processing_method,
                    'slicing_used': 'slicing' in processing_method,
                    'slicing_info': slicing_info
                },
                'fallback_info': {
                    'level': 'ocr_with_slicing',
                    'reason': 'vision_analysis_failed',
                    'capabilities': [
                        'text_recognition', 
                        'intelligent_slicing',
                        'coordinate_mapping',
                        'duplicate_removal'
                    ],
                    'enhancement': 'intelligent_slicing_enabled'
                }
            }
            
            # 如果使用了切片，添加切片统计信息
            if slicing_info:
                standardized_result['slicing_statistics'] = {
                    'total_slices': slicing_info.get('total_slices', 0),
                    'successful_slices': slicing_info.get('successful_slices', 0),
                    'success_rate': slicing_info.get('success_rate', 0.0)
                }
            
            total_regions = standardized_result['statistics']['total_text_regions']
            method_desc = "切片OCR" if 'slicing' in processing_method else "直接OCR"
            
            logger.info(f"OCR降级分析完成 - 任务ID: {task_id}, 方法: {method_desc}, "
                       f"识别文本区域: {total_regions}")
            
            return standardized_result
            
        except Exception as e:
            logger.error(f"OCR降级分析失败 - 任务ID: {task_id}: {e}")
            raise Exception(f"OCR降级分析失败: {str(e)}") 