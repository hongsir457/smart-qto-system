#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能切片Vision分析降级处理策略
提供多层次的错误恢复和降级机制
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

class FallbackLevel(Enum):
    """降级级别"""
    LEVEL_0 = "normal"           # 正常处理
    LEVEL_1 = "retry_slicing"    # 重试切片分析
    LEVEL_2 = "direct_analysis"  # 降级到直接分析
    LEVEL_3 = "simple_ocr"       # 降级到简单OCR
    LEVEL_4 = "basic_info"       # 降级到基础信息
    LEVEL_5 = "error_report"     # 最终错误报告

@dataclass
class FallbackResult:
    """降级结果"""
    level: FallbackLevel
    success: bool
    data: Dict[str, Any]
    error_message: str = ""
    processing_time: float = 0.0
    fallback_reason: str = ""

class VisionAnalysisFallbackStrategy:
    """Vision分析降级处理策略"""
    
    def __init__(self):
        """初始化降级策略"""
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]  # 递增延迟
        self.timeout_thresholds = {
            FallbackLevel.LEVEL_0: 300,  # 5分钟
            FallbackLevel.LEVEL_1: 180,  # 3分钟
            FallbackLevel.LEVEL_2: 60,   # 1分钟
            FallbackLevel.LEVEL_3: 30,   # 30秒
        }
        
    async def execute_with_fallback(self, 
                                  primary_func: Callable,
                                  fallback_funcs: List[Callable],
                                  task_id: str,
                                  **kwargs) -> FallbackResult:
        """
        执行带降级策略的分析
        
        Args:
            primary_func: 主要处理函数
            fallback_funcs: 降级处理函数列表
            task_id: 任务ID
            **kwargs: 其他参数
            
        Returns:
            降级结果
        """
        logger.info(f"开始执行带降级策略的分析 - 任务ID: {task_id}")
        
        # Level 0: 正常切片分析
        result = await self._try_level_0(primary_func, task_id, **kwargs)
        if result.success:
            return result
        
        # Level 1: 重试切片分析
        result = await self._try_level_1(primary_func, task_id, **kwargs)
        if result.success:
            return result
        
        # Level 2: 降级到直接分析
        if len(fallback_funcs) > 0:
            result = await self._try_level_2(fallback_funcs[0], task_id, **kwargs)
            if result.success:
                return result
        
        # Level 3: 降级到简单OCR
        if len(fallback_funcs) > 1:
            result = await self._try_level_3(fallback_funcs[1], task_id, **kwargs)
            if result.success:
                return result
        
        # Level 4: 降级到基础信息
        result = await self._try_level_4(task_id, **kwargs)
        if result.success:
            return result
        
        # Level 5: 最终错误报告
        return await self._try_level_5(task_id, **kwargs)
    
    async def _try_level_0(self, func: Callable, task_id: str, **kwargs) -> FallbackResult:
        """Level 0: 正常切片分析"""
        logger.info(f"Level 0: 尝试正常切片分析 - {task_id}")
        
        start_time = time.time()
        
        try:
            # 设置超时
            result = await asyncio.wait_for(
                func(**kwargs),
                timeout=self.timeout_thresholds[FallbackLevel.LEVEL_0]
            )
            
            processing_time = time.time() - start_time
            
            # 验证结果质量
            if self._validate_slice_result(result):
                logger.info(f"Level 0 成功 - {task_id}, 耗时: {processing_time:.2f}s")
                return FallbackResult(
                    level=FallbackLevel.LEVEL_0,
                    success=True,
                    data=result,
                    processing_time=processing_time
                )
            else:
                raise Exception("切片分析结果质量不达标")
                
        except asyncio.TimeoutError:
            error_msg = f"Level 0 超时 - {task_id}"
            logger.warning(error_msg)
            return FallbackResult(
                level=FallbackLevel.LEVEL_0,
                success=False,
                data={},
                error_message=error_msg,
                processing_time=time.time() - start_time,
                fallback_reason="timeout"
            )
        except Exception as e:
            error_msg = f"Level 0 失败 - {task_id}: {str(e)}"
            logger.warning(error_msg)
            return FallbackResult(
                level=FallbackLevel.LEVEL_0,
                success=False,
                data={},
                error_message=error_msg,
                processing_time=time.time() - start_time,
                fallback_reason="error"
            )
    
    async def _try_level_1(self, func: Callable, task_id: str, **kwargs) -> FallbackResult:
        """Level 1: 重试切片分析（优化参数）"""
        logger.info(f"Level 1: 重试切片分析（优化参数）- {task_id}")
        
        # 优化参数：减少切片数量，提高成功率
        optimized_kwargs = kwargs.copy()
        if 'slicer_config' in optimized_kwargs:
            optimized_kwargs['slicer_config'] = {
                'max_resolution': 1024,  # 降低分辨率
                'overlap_ratio': 0.05,   # 减少重叠
                'quality': 90,           # 降低质量
                'max_slices': 6          # 限制切片数
            }
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Level 1 重试 {attempt + 1}/{self.max_retries} - {task_id}")
                
                result = await asyncio.wait_for(
                    func(**optimized_kwargs),
                    timeout=self.timeout_thresholds[FallbackLevel.LEVEL_1]
                )
                
                processing_time = time.time() - start_time
                
                if self._validate_slice_result(result, min_success_rate=0.5):
                    logger.info(f"Level 1 成功 - {task_id}, 尝试: {attempt + 1}, 耗时: {processing_time:.2f}s")
                    return FallbackResult(
                        level=FallbackLevel.LEVEL_1,
                        success=True,
                        data=result,
                        processing_time=processing_time,
                        fallback_reason="retry_with_optimization"
                    )
                
            except Exception as e:
                logger.warning(f"Level 1 重试 {attempt + 1} 失败 - {task_id}: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
        
        error_msg = f"Level 1 最终失败 - {task_id}"
        logger.warning(error_msg)
        return FallbackResult(
            level=FallbackLevel.LEVEL_1,
            success=False,
            data={},
            error_message=error_msg,
            processing_time=time.time() - start_time,
            fallback_reason="max_retries_exceeded"
        )
    
    async def _try_level_2(self, direct_func: Callable, task_id: str, **kwargs) -> FallbackResult:
        """Level 2: 降级到直接分析"""
        logger.info(f"Level 2: 降级到直接分析 - {task_id}")
        
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                direct_func(**kwargs),
                timeout=self.timeout_thresholds[FallbackLevel.LEVEL_2]
            )
            
            processing_time = time.time() - start_time
            
            if self._validate_direct_result(result):
                logger.info(f"Level 2 成功 - {task_id}, 耗时: {processing_time:.2f}s")
                return FallbackResult(
                    level=FallbackLevel.LEVEL_2,
                    success=True,
                    data=result,
                    processing_time=processing_time,
                    fallback_reason="fallback_to_direct_analysis"
                )
            else:
                raise Exception("直接分析结果质量不达标")
                
        except Exception as e:
            error_msg = f"Level 2 失败 - {task_id}: {str(e)}"
            logger.warning(error_msg)
            return FallbackResult(
                level=FallbackLevel.LEVEL_2,
                success=False,
                data={},
                error_message=error_msg,
                processing_time=time.time() - start_time,
                fallback_reason="direct_analysis_failed"
            )
    
    async def _try_level_3(self, ocr_func: Callable, task_id: str, **kwargs) -> FallbackResult:
        """Level 3: 降级到简单OCR"""
        logger.info(f"Level 3: 降级到简单OCR - {task_id}")
        
        start_time = time.time()
        
        try:
            # 使用PaddleOCR进行基础文字识别
            ocr_result = await asyncio.wait_for(
                ocr_func(**kwargs),
                timeout=self.timeout_thresholds[FallbackLevel.LEVEL_3]
            )
            
            processing_time = time.time() - start_time
            
            # 转换OCR结果为标准格式
            standardized_result = self._convert_ocr_to_standard_format(ocr_result, task_id)
            
            logger.info(f"Level 3 成功 - {task_id}, 识别文本: {len(standardized_result.get('texts', []))}, 耗时: {processing_time:.2f}s")
            return FallbackResult(
                level=FallbackLevel.LEVEL_3,
                success=True,
                data=standardized_result,
                processing_time=processing_time,
                fallback_reason="fallback_to_ocr_only"
            )
            
        except Exception as e:
            error_msg = f"Level 3 失败 - {task_id}: {str(e)}"
            logger.warning(error_msg)
            return FallbackResult(
                level=FallbackLevel.LEVEL_3,
                success=False,
                data={},
                error_message=error_msg,
                processing_time=time.time() - start_time,
                fallback_reason="ocr_failed"
            )
    
    async def _try_level_4(self, task_id: str, **kwargs) -> FallbackResult:
        """Level 4: 降级到基础信息"""
        logger.info(f"Level 4: 降级到基础信息 - {task_id}")
        
        start_time = time.time()
        
        try:
            # 提取基础图像信息
            image_path = kwargs.get('image_path')
            basic_info = await self._extract_basic_image_info(image_path)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Level 4 成功 - {task_id}, 耗时: {processing_time:.2f}s")
            return FallbackResult(
                level=FallbackLevel.LEVEL_4,
                success=True,
                data=basic_info,
                processing_time=processing_time,
                fallback_reason="fallback_to_basic_info"
            )
            
        except Exception as e:
            error_msg = f"Level 4 失败 - {task_id}: {str(e)}"
            logger.error(error_msg)
            return FallbackResult(
                level=FallbackLevel.LEVEL_4,
                success=False,
                data={},
                error_message=error_msg,
                processing_time=time.time() - start_time,
                fallback_reason="basic_info_failed"
            )
    
    async def _try_level_5(self, task_id: str, **kwargs) -> FallbackResult:
        """Level 5: 最终错误报告"""
        logger.error(f"Level 5: 生成最终错误报告 - {task_id}")
        
        error_report = {
            'task_id': task_id,
            'status': 'completely_failed',
            'error_summary': '所有处理级别都失败了',
            'attempted_levels': [
                'intelligent_slicing',
                'retry_slicing',
                'direct_analysis',
                'simple_ocr',
                'basic_info'
            ],
            'recommendations': [
                '检查图像文件是否损坏',
                '验证OpenAI API密钥权限',
                '确认网络连接正常',
                '尝试减小图像尺寸',
                '联系技术支持'
            ],
            'timestamp': time.time()
        }
        
        return FallbackResult(
            level=FallbackLevel.LEVEL_5,
            success=False,
            data=error_report,
            error_message="所有降级策略都失败了",
            fallback_reason="complete_failure"
        )
    
    def _validate_slice_result(self, result: Dict[str, Any], min_success_rate: float = 0.8) -> bool:
        """验证切片分析结果质量"""
        try:
            if not result or not isinstance(result, dict):
                return False
            
            processing_summary = result.get('processing_summary', {})
            success_rate = processing_summary.get('success_rate', 0)
            total_components = processing_summary.get('total_components', 0)
            
            # 检查成功率和构件数量
            return success_rate >= min_success_rate and total_components > 0
            
        except Exception:
            return False
    
    def _validate_direct_result(self, result: Dict[str, Any]) -> bool:
        """验证直接分析结果质量"""
        try:
            if not result or not isinstance(result, dict):
                return False
            
            analysis_result = result.get('analysis_result', {})
            components = analysis_result.get('components', [])
            
            # 至少要有一些识别结果
            return len(components) > 0 or len(analysis_result.get('detected_elements', [])) > 0
            
        except Exception:
            return False
    
    def _convert_ocr_to_standard_format(self, ocr_result: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """将OCR结果转换为标准格式"""
        try:
            texts = ocr_result.get('texts', [])
            
            # 简单的构件类型识别
            detected_components = []
            component_keywords = {
                '柱': 'column',
                '梁': 'beam',
                '板': 'slab',
                '墙': 'wall',
                '基础': 'foundation',
                '楼梯': 'stair'
            }
            
            for i, text_info in enumerate(texts):
                text = text_info.get('text', '')
                bbox = text_info.get('bbox', [0, 0, 100, 100])
                
                for keyword, comp_type in component_keywords.items():
                    if keyword in text:
                        component = {
                            'id': f"{task_id}_ocr_comp_{i}",
                            'type': comp_type,
                            'name': text,
                            'bbox': bbox,
                            'confidence': text_info.get('confidence', 0.8),
                            'source': 'ocr_fallback'
                        }
                        detected_components.append(component)
                        break
            
            return {
                'task_id': task_id,
                'analysis_type': 'ocr_fallback',
                'texts': texts,
                'components': detected_components,
                'statistics': {
                    'total_texts': len(texts),
                    'total_components': len(detected_components),
                    'confidence_avg': sum(t.get('confidence', 0.8) for t in texts) / len(texts) if texts else 0
                },
                'fallback_info': {
                    'level': 'ocr_only',
                    'reason': 'vision_analysis_failed'
                }
            }
            
        except Exception as e:
            logger.error(f"OCR结果转换失败: {e}")
            return {
                'task_id': task_id,
                'analysis_type': 'ocr_fallback',
                'texts': [],
                'components': [],
                'error': str(e)
            }
    
    async def _extract_basic_image_info(self, image_path: str) -> Dict[str, Any]:
        """提取基础图像信息"""
        try:
            from PIL import Image
            import os
            
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError("图像文件不存在")
            
            with Image.open(image_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format
                
                # 获取文件信息
                file_size = os.path.getsize(image_path)
                file_name = os.path.basename(image_path)
                
                # 尝试获取DPI信息
                dpi = img.info.get('dpi', (72, 72))
                if isinstance(dpi, tuple):
                    dpi_x, dpi_y = dpi
                else:
                    dpi_x = dpi_y = dpi
                
                return {
                    'task_type': 'basic_image_info',
                    'file_info': {
                        'name': file_name,
                        'size_bytes': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2)
                    },
                    'image_properties': {
                        'width': width,
                        'height': height,
                        'mode': mode,
                        'format': format_name,
                        'dpi': (dpi_x, dpi_y),
                        'total_pixels': width * height
                    },
                    'analysis_info': {
                        'suitable_for_slicing': max(width, height) > 2048,
                        'estimated_slice_count': self._estimate_slice_count(width, height),
                        'recommended_method': 'slicing' if max(width, height) > 2048 else 'direct'
                    },
                    'fallback_info': {
                        'level': 'basic_info_only',
                        'reason': 'all_analysis_methods_failed',
                        'recommendations': [
                            '检查图像文件完整性',
                            '验证API配置',
                            '尝试其他分析方法'
                        ]
                    }
                }
                
        except Exception as e:
            raise Exception(f"无法提取基础图像信息: {str(e)}")
    
    def _estimate_slice_count(self, width: int, height: int) -> int:
        """估算切片数量"""
        if max(width, height) <= 2048:
            return 1
        
        slice_width = 2048
        slice_height = 2048
        overlap = 0.1
        
        effective_width = slice_width * (1 - overlap)
        effective_height = slice_height * (1 - overlap)
        
        slices_x = max(1, int(width / effective_width) + (1 if width % effective_width > 0 else 0))
        slices_y = max(1, int(height / effective_height) + (1 if height % effective_height > 0 else 0))
        
        return slices_x * slices_y

# 全局降级策略实例
fallback_strategy = VisionAnalysisFallbackStrategy() 