#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR服务接口 - 集成智能切片功能
提供统一的OCR处理接口，自动选择是否使用切片
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from app.services.ocr.paddle_ocr import PaddleOCRService as OriginalPaddleOCRService
from app.services.ocr.paddle_ocr_with_slicing import PaddleOCRWithSlicing

logger = logging.getLogger(__name__)

class PaddleOCRService:
    """
    增强版PaddleOCR服务
    自动判断是否使用智能切片，提供最佳OCR效果
    """
    
    def __init__(self):
        """初始化服务"""
        self.original_service = OriginalPaddleOCRService()
        self.slicing_service = PaddleOCRWithSlicing()
        
        # 配置参数
        self.auto_slicing = True  # 是否自动启用切片
        self.slice_threshold = 2048  # 切片阈值
        
        logger.info("🚀 增强版PaddleOCR服务初始化完成")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return (self.original_service.is_available() and 
                self.slicing_service.is_available())
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'original_service': self.original_service.get_status(),
            'slicing_service': self.slicing_service.is_available(),
            'auto_slicing_enabled': self.auto_slicing,
            'slice_threshold': self.slice_threshold,
            'is_available': self.is_available()
        }
    
    async def process_image_async(self, image_path: str, use_slicing: Optional[bool] = None) -> Dict[str, Any]:
        """
        异步处理图像OCR
        
        Args:
            image_path: 图像文件路径
            use_slicing: 是否强制使用切片（None=自动判断）
            
        Returns:
            OCR结果
        """
        logger.info(f"开始OCR处理: {Path(image_path).name}")
        
        try:
            # 决定是否使用切片
            should_use_slicing = await self._should_use_slicing(image_path, use_slicing)
            
            if should_use_slicing:
                logger.info("使用智能切片OCR处理")
                result = await self.slicing_service.process_image_async(image_path)
                result['processing_method'] = 'slicing_ocr'
            else:
                logger.info("使用直接OCR处理")
                result = await self._process_with_original_service(image_path)
                result['processing_method'] = 'direct_ocr'
            
            logger.info(f"OCR处理完成: {result.get('statistics', {}).get('total_regions', 0)} 个文本区域")
            return result
            
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'texts': [],
                'text_regions': [],
                'all_text': '',
                'statistics': {'total_regions': 0, 'avg_confidence': 0, 'processing_time': 0},
                'processing_method': 'failed'
            }
    
    def recognize_text(self, 
                      image_path: str, 
                      save_to_sealos: bool = True, 
                      drawing_id: str = None,
                      use_slicing: Optional[bool] = None) -> Dict[str, Any]:
        """
        同步接口 - 识别文本（兼容原始接口）
        
        Args:
            image_path: 图像文件路径
            save_to_sealos: 是否保存到云存储
            drawing_id: 图纸ID
            use_slicing: 是否使用切片
            
        Returns:
            OCR结果
        """
        try:
            # 在事件循环中运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    self.process_image_async(image_path, use_slicing)
                )
                
                # 如果需要保存到云存储且使用了切片，则已经在切片服务中处理了
                # 对于直接OCR，可能需要额外处理保存逻辑
                if save_to_sealos and result.get('processing_method') == 'direct_ocr':
                    # 这里可以添加保存逻辑，或者调用原始服务的保存功能
                    pass
                
                return result
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"同步OCR处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'text_regions': [],
                'all_text': '',
                'statistics': {'total_regions': 0, 'avg_confidence': 0}
            }
    
    async def _should_use_slicing(self, image_path: str, force_slicing: Optional[bool]) -> bool:
        """判断是否应该使用切片"""
        
        # 如果强制指定，则使用指定值
        if force_slicing is not None:
            return force_slicing
        
        # 如果未启用自动切片，则不使用
        if not self.auto_slicing:
            return False
        
        # 检查切片服务是否可用
        if not self.slicing_service.is_available():
            logger.warning("切片服务不可用，使用直接OCR")
            return False
        
        # 根据图像尺寸判断
        try:
            import cv2
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            height, width = img.shape[:2]
            max_dimension = max(width, height)
            
            should_slice = max_dimension > self.slice_threshold
            logger.info(f"图像尺寸: {width}x{height}, 使用切片: {should_slice}")
            
            return should_slice
            
        except Exception as e:
            logger.error(f"检查图像尺寸失败: {e}")
            return False
    
    async def _process_with_original_service(self, image_path: str) -> Dict[str, Any]:
        """使用原始服务处理"""
        try:
            # 在线程池中运行同步方法
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.original_service.recognize_text,
                image_path,
                False,  # save_to_sealos
                None    # drawing_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"原始OCR服务处理失败: {e}")
            raise
    
    def set_auto_slicing(self, enabled: bool):
        """设置是否自动启用切片"""
        self.auto_slicing = enabled
        logger.info(f"自动切片设置: {enabled}")
    
    def set_slice_threshold(self, threshold: int):
        """设置切片阈值"""
        self.slice_threshold = threshold
        logger.info(f"切片阈值设置: {threshold}")
    
    async def process_with_slicing_forced(self, image_path: str, task_id: str = None) -> Dict[str, Any]:
        """强制使用切片处理"""
        logger.info(f"强制使用切片OCR处理: {Path(image_path).name}")
        
        try:
            merged_result = await self.slicing_service.process_image_with_slicing(
                image_path=image_path,
                task_id=task_id,
                save_to_storage=True
            )
            
            # 转换为标准格式
            return {
                'success': merged_result.success_rate > 0,
                'texts': [
                    {
                        'text': region.get('text', ''),
                        'bbox': region.get('bbox', []),
                        'confidence': region.get('confidence', 0.0)
                    }
                    for region in merged_result.merged_text_regions
                ],
                'text_regions': merged_result.merged_text_regions,
                'all_text': merged_result.all_text,
                'statistics': {
                    'total_regions': merged_result.total_text_regions,
                    'avg_confidence': merged_result.processing_summary['ocr_statistics']['avg_confidence'],
                    'processing_time': merged_result.processing_time
                },
                'processing_summary': merged_result.processing_summary,
                'processing_method': 'forced_slicing_ocr',
                'slicing_info': {
                    'total_slices': merged_result.total_slices,
                    'successful_slices': merged_result.successful_slices,
                    'success_rate': merged_result.success_rate
                }
            }
            
        except Exception as e:
            logger.error(f"强制切片OCR处理失败: {e}")
            raise
    
    async def compare_methods(self, image_path: str) -> Dict[str, Any]:
        """比较直接OCR和切片OCR的效果"""
        logger.info(f"比较OCR方法: {Path(image_path).name}")
        
        results = {}
        
        try:
            # 直接OCR
            logger.info("执行直接OCR...")
            direct_result = await self._process_with_original_service(image_path)
            results['direct_ocr'] = direct_result
            
        except Exception as e:
            logger.error(f"直接OCR失败: {e}")
            results['direct_ocr'] = {'success': False, 'error': str(e)}
        
        try:
            # 切片OCR
            logger.info("执行切片OCR...")
            slicing_result = await self.slicing_service.process_image_async(image_path)
            results['slicing_ocr'] = slicing_result
            
        except Exception as e:
            logger.error(f"切片OCR失败: {e}")
            results['slicing_ocr'] = {'success': False, 'error': str(e)}
        
        # 生成比较报告
        comparison = self._generate_comparison_report(results)
        results['comparison'] = comparison
        
        return results
    
    def _generate_comparison_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成比较报告"""
        
        direct = results.get('direct_ocr', {})
        slicing = results.get('slicing_ocr', {})
        
        comparison = {
            'direct_ocr': {
                'success': direct.get('success', False),
                'text_regions': direct.get('statistics', {}).get('total_regions', 0),
                'avg_confidence': direct.get('statistics', {}).get('avg_confidence', 0),
                'processing_time': direct.get('statistics', {}).get('processing_time', 0)
            },
            'slicing_ocr': {
                'success': slicing.get('success', False),
                'text_regions': slicing.get('statistics', {}).get('total_regions', 0),
                'avg_confidence': slicing.get('statistics', {}).get('avg_confidence', 0),
                'processing_time': slicing.get('statistics', {}).get('processing_time', 0),
                'slices_info': slicing.get('processing_summary', {}).get('slicing_info', {})
            }
        }
        
        # 计算改进指标
        if direct.get('success') and slicing.get('success'):
            direct_regions = comparison['direct_ocr']['text_regions']
            slicing_regions = comparison['slicing_ocr']['text_regions']
            
            if direct_regions > 0:
                improvement = {
                    'text_regions_improvement': (slicing_regions - direct_regions) / direct_regions,
                    'confidence_improvement': comparison['slicing_ocr']['avg_confidence'] - comparison['direct_ocr']['avg_confidence'],
                    'processing_time_ratio': comparison['slicing_ocr']['processing_time'] / comparison['direct_ocr']['processing_time']
                }
                comparison['improvement'] = improvement
        
        # 推荐方法
        if slicing.get('success') and direct.get('success'):
            slicing_score = comparison['slicing_ocr']['text_regions'] * comparison['slicing_ocr']['avg_confidence']
            direct_score = comparison['direct_ocr']['text_regions'] * comparison['direct_ocr']['avg_confidence']
            
            if slicing_score > direct_score * 1.2:  # 切片效果显著更好
                recommendation = 'slicing_ocr'
                reason = '切片OCR识别效果显著更好'
            elif direct_score > slicing_score and comparison['direct_ocr']['processing_time'] < comparison['slicing_ocr']['processing_time']:
                recommendation = 'direct_ocr'
                reason = '直接OCR效果相当且速度更快'
            else:
                recommendation = 'slicing_ocr'
                reason = '切片OCR更适合大图像处理'
        elif slicing.get('success'):
            recommendation = 'slicing_ocr'
            reason = '只有切片OCR成功'
        elif direct.get('success'):
            recommendation = 'direct_ocr'
            reason = '只有直接OCR成功'
        else:
            recommendation = 'none'
            reason = '两种方法都失败'
        
        comparison['recommendation'] = {
            'method': recommendation,
            'reason': reason
        }
        
        return comparison 