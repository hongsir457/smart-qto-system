#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成智能切片功能的PaddleOCR服务
将智能切片模块提前到OCR处理阶段，提高OCR精度和处理效果
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np
from dataclasses import dataclass
import json
import uuid

from app.services.intelligent_image_slicer import IntelligentImageSlicer, SliceInfo
from app.services.ocr.paddle_ocr import PaddleOCRService
from app.services.dual_storage_service import DualStorageService

logger = logging.getLogger(__name__)

@dataclass
class OCRSliceResult:
    """OCR切片结果"""
    slice_id: str
    slice_index: int
    slice_bounds: Tuple[int, int, int, int]  # (x, y, width, height)
    slice_path: str
    ocr_result: Dict[str, Any]
    text_regions: List[Dict[str, Any]]
    processing_time: float
    success: bool
    error_message: str = ""

@dataclass
class MergedOCRResult:
    """合并后的OCR结果"""
    task_id: str
    total_slices: int
    successful_slices: int
    success_rate: float
    total_text_regions: int
    merged_text_regions: List[Dict[str, Any]]
    all_text: str
    processing_summary: Dict[str, Any]
    slice_results: List[OCRSliceResult]
    processing_time: float

class PaddleOCRWithSlicing:
    """
    PaddleOCR with intelligent slicing support - 使用双重存储
    """
    
    def __init__(self):
        """初始化OCR切片服务"""
        self.ocr_service = PaddleOCRService()
        self.slicer = IntelligentImageSlicer()
        
        # 使用双重存储服务
        try:
            self.storage = DualStorageService()
            logger.info("✅ PaddleOCRWithSlicing 使用双重存储服务")
        except Exception as e:
            logger.error(f"双重存储服务初始化失败: {e}")
            self.storage = None
        
        # 切片配置
        self.slice_config = {
            'max_resolution': 2048,      # OCR切片最大分辨率
            'overlap_ratio': 0.15,       # OCR需要更多重叠以确保文字完整
            'quality': 95,               # OCR需要高质量图像
            'min_slice_size': 512,       # 最小切片尺寸
            'max_slices': 16             # OCR最大切片数
        }
        
        logger.info("🔧 PaddleOCR智能切片服务初始化完成")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return (self.slicer.is_available() and 
                self.ocr_service.is_available())
    
    async def process_image_with_slicing(self, 
                                       image_path: str, 
                                       task_id: str = None,
                                       save_to_storage: bool = True) -> MergedOCRResult:
        """
        使用智能切片处理图像OCR
        
        Args:
            image_path: 图像文件路径
            task_id: 任务ID
            save_to_storage: 是否保存到云存储
            
        Returns:
            合并后的OCR结果
        """
        if not task_id:
            task_id = f"ocr_slice_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🚀 开始智能切片OCR处理 - 任务ID: {task_id}")
        start_time = time.time()
        
        try:
            # 1. 检查是否需要切片
            needs_slicing = await self._should_slice_image(image_path)
            
            if not needs_slicing:
                logger.info(f"图像尺寸适中，使用直接OCR处理 - {task_id}")
                return await self._process_direct_ocr(image_path, task_id, save_to_storage)
            
            # 2. 执行智能切片
            logger.info(f"执行智能切片 - {task_id}")
            slice_info = await self._execute_image_slicing(image_path, task_id)
            
            if not slice_info or not slice_info.slices:
                logger.warning(f"切片失败，回退到直接OCR - {task_id}")
                return await self._process_direct_ocr(image_path, task_id, save_to_storage)
            
            # 3. 并行处理所有切片的OCR
            logger.info(f"并行处理 {len(slice_info.slices)} 个切片的OCR - {task_id}")
            slice_results = await self._process_slices_ocr(slice_info, task_id)
            
            # 4. 合并OCR结果
            logger.info(f"合并OCR结果 - {task_id}")
            merged_result = await self._merge_ocr_results(
                slice_results, slice_info, task_id, start_time
            )
            
            # 5. 保存结果到双重存储
            if save_to_storage:
                await self._save_results_to_storage(merged_result, task_id)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ 智能切片OCR完成 - {task_id}, 耗时: {processing_time:.2f}s, "
                       f"识别文本: {merged_result.total_text_regions}")
            
            return merged_result
            
        except Exception as e:
            logger.error(f"❌ 智能切片OCR失败 - {task_id}: {e}")
            # 回退到直接OCR
            try:
                logger.info(f"回退到直接OCR处理 - {task_id}")
                return await self._process_direct_ocr(image_path, task_id, save_to_storage)
            except Exception as fallback_error:
                logger.error(f"❌ 直接OCR回退也失败 - {task_id}: {fallback_error}")
                raise Exception(f"OCR处理完全失败: {str(e)} | 回退错误: {str(fallback_error)}")
    
    async def _should_slice_image(self, image_path: str) -> bool:
        """判断是否需要对图像进行切片"""
        try:
            with cv2.imread(image_path) as img:
                if img is None:
                    return False
                
                height, width = img.shape[:2]
                max_dimension = max(width, height)
                total_pixels = width * height
                
                # 判断条件
                needs_slicing = (
                    max_dimension > self.slice_config['max_resolution'] or
                    total_pixels > 4_000_000  # 4M像素以上
                )
                
                logger.info(f"图像尺寸: {width}x{height}, 是否需要切片: {needs_slicing}")
                return needs_slicing
                
        except Exception as e:
            logger.error(f"检查图像尺寸失败: {e}")
            return False
    
    async def _execute_image_slicing(self, image_path: str, task_id: str) -> SliceInfo:
        """执行图像切片"""
        try:
            slice_info = await self.slicer.slice_image_async(
                image_path=image_path,
                max_resolution=self.slice_config['max_resolution'],
                overlap_ratio=self.slice_config['overlap_ratio'],
                quality=self.slice_config['quality'],
                output_dir=f"ocr_slices_{task_id}"
            )
            
            logger.info(f"切片完成: {len(slice_info.slices)} 个切片")
            return slice_info
            
        except Exception as e:
            logger.error(f"图像切片失败: {e}")
            raise
    
    async def _process_slices_ocr(self, slice_info: SliceInfo, task_id: str) -> List[OCRSliceResult]:
        """并行处理所有切片的OCR"""
        
        async def process_single_slice(slice_data, index) -> OCRSliceResult:
            """处理单个切片的OCR"""
            slice_id = f"{task_id}_slice_{index}"
            start_time = time.time()
            
            try:
                logger.debug(f"处理切片 {index+1}/{len(slice_info.slices)} - {slice_id}")
                
                # 调用PaddleOCR处理切片
                ocr_result = self.ocr_service.recognize_text(
                    image_path=slice_data.path,
                    save_to_sealos=False,  # 不保存单个切片结果
                    drawing_id=slice_id
                )
                
                processing_time = time.time() - start_time
                
                # 转换坐标到原图坐标系
                adjusted_text_regions = self._adjust_coordinates_to_original(
                    ocr_result.get('text_regions', []),
                    slice_data.bounds
                )
                
                return OCRSliceResult(
                    slice_id=slice_id,
                    slice_index=index,
                    slice_bounds=slice_data.bounds,
                    slice_path=slice_data.path,
                    ocr_result=ocr_result,
                    text_regions=adjusted_text_regions,
                    processing_time=processing_time,
                    success=ocr_result.get('success', False)
                )
                
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"切片 {slice_id} OCR失败: {e}")
                
                return OCRSliceResult(
                    slice_id=slice_id,
                    slice_index=index,
                    slice_bounds=slice_data.bounds,
                    slice_path=slice_data.path,
                    ocr_result={},
                    text_regions=[],
                    processing_time=processing_time,
                    success=False,
                    error_message=str(e)
                )
        
        # 并行处理所有切片
        logger.info(f"开始并行处理 {len(slice_info.slices)} 个切片的OCR")
        
        # 限制并发数量以避免资源耗尽
        semaphore = asyncio.Semaphore(4)  # 最多4个并发OCR
        
        async def process_with_semaphore(slice_data, index):
            async with semaphore:
                return await process_single_slice(slice_data, index)
        
        tasks = [
            process_with_semaphore(slice_data, index)
            for index, slice_data in enumerate(slice_info.slices)
        ]
        
        slice_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        valid_results = []
        for i, result in enumerate(slice_results):
            if isinstance(result, Exception):
                logger.error(f"切片 {i} 处理异常: {result}")
                # 创建失败结果
                error_result = OCRSliceResult(
                    slice_id=f"{task_id}_slice_{i}",
                    slice_index=i,
                    slice_bounds=(0, 0, 0, 0),
                    slice_path="",
                    ocr_result={},
                    text_regions=[],
                    processing_time=0,
                    success=False,
                    error_message=str(result)
                )
                valid_results.append(error_result)
            else:
                valid_results.append(result)
        
        successful_count = sum(1 for r in valid_results if r.success)
        logger.info(f"OCR处理完成: {successful_count}/{len(valid_results)} 个切片成功")
        
        return valid_results
    
    def _adjust_coordinates_to_original(self, 
                                      text_regions: List[Dict[str, Any]], 
                                      slice_bounds: Tuple[int, int, int, int]) -> List[Dict[str, Any]]:
        """将切片坐标调整到原图坐标系"""
        
        x_offset, y_offset, _, _ = slice_bounds
        adjusted_regions = []
        
        for region in text_regions:
            adjusted_region = region.copy()
            
            # 调整边界框坐标
            if 'bbox' in adjusted_region:
                bbox = adjusted_region['bbox']
                if isinstance(bbox, list) and len(bbox) == 4:
                    # 格式: [x1, y1, x2, y2]
                    adjusted_region['bbox'] = [
                        bbox[0] + x_offset,
                        bbox[1] + y_offset,
                        bbox[2] + x_offset,
                        bbox[3] + y_offset
                    ]
            
            # 调整多边形坐标（如果存在）
            if 'polygon' in adjusted_region:
                polygon = adjusted_region['polygon']
                if isinstance(polygon, list):
                    adjusted_polygon = []
                    for point in polygon:
                        if isinstance(point, list) and len(point) == 2:
                            adjusted_polygon.append([
                                point[0] + x_offset,
                                point[1] + y_offset
                            ])
                    adjusted_region['polygon'] = adjusted_polygon
            
            # 添加切片信息
            adjusted_region['source_slice'] = {
                'slice_bounds': slice_bounds,
                'original_bbox': region.get('bbox'),
                'original_polygon': region.get('polygon')
            }
            
            adjusted_regions.append(adjusted_region)
        
        return adjusted_regions
    
    async def _merge_ocr_results(self, 
                               slice_results: List[OCRSliceResult],
                               slice_info: SliceInfo,
                               task_id: str,
                               start_time: float) -> MergedOCRResult:
        """合并所有切片的OCR结果"""
        
        logger.info(f"开始合并 {len(slice_results)} 个切片的OCR结果")
        
        # 收集所有文本区域
        all_text_regions = []
        all_texts = []
        successful_slices = 0
        
        for slice_result in slice_results:
            if slice_result.success:
                successful_slices += 1
                all_text_regions.extend(slice_result.text_regions)
                
                # 收集文本内容
                for region in slice_result.text_regions:
                    text = region.get('text', '').strip()
                    if text:
                        all_texts.append(text)
        
        # 去重重叠区域的文本
        deduplicated_regions = self._remove_duplicate_text_regions(all_text_regions)
        
        # 重新收集去重后的文本
        final_texts = []
        for region in deduplicated_regions:
            text = region.get('text', '').strip()
            if text:
                final_texts.append(text)
        
        # 生成处理摘要
        processing_summary = {
            'original_image': {
                'width': slice_info.original_width,
                'height': slice_info.original_height,
                'total_pixels': slice_info.original_width * slice_info.original_height
            },
            'slicing_info': {
                'total_slices': len(slice_results),
                'successful_slices': successful_slices,
                'success_rate': successful_slices / len(slice_results) if slice_results else 0,
                'slice_config': self.slice_config
            },
            'ocr_statistics': {
                'total_text_regions_before_dedup': len(all_text_regions),
                'total_text_regions_after_dedup': len(deduplicated_regions),
                'deduplication_rate': 1 - (len(deduplicated_regions) / len(all_text_regions)) if all_text_regions else 0,
                'total_characters': sum(len(text) for text in final_texts),
                'avg_confidence': self._calculate_average_confidence(deduplicated_regions)
            },
            'performance': {
                'total_processing_time': time.time() - start_time,
                'avg_slice_processing_time': sum(r.processing_time for r in slice_results) / len(slice_results) if slice_results else 0
            }
        }
        
        merged_result = MergedOCRResult(
            task_id=task_id,
            total_slices=len(slice_results),
            successful_slices=successful_slices,
            success_rate=successful_slices / len(slice_results) if slice_results else 0,
            total_text_regions=len(deduplicated_regions),
            merged_text_regions=deduplicated_regions,
            all_text='\n'.join(final_texts),
            processing_summary=processing_summary,
            slice_results=slice_results,
            processing_time=time.time() - start_time
        )
        
        logger.info(f"OCR结果合并完成: {len(deduplicated_regions)} 个文本区域, "
                   f"去重率: {processing_summary['ocr_statistics']['deduplication_rate']:.2%}")
        
        return merged_result
    
    def _remove_duplicate_text_regions(self, text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重叠区域的重复文本"""
        
        if not text_regions:
            return []
        
        # 按置信度排序（高置信度优先）
        sorted_regions = sorted(
            text_regions, 
            key=lambda x: x.get('confidence', 0), 
            reverse=True
        )
        
        deduplicated = []
        
        for current_region in sorted_regions:
            current_text = current_region.get('text', '').strip()
            current_bbox = current_region.get('bbox', [0, 0, 0, 0])
            
            if not current_text:
                continue
            
            # 检查是否与已有区域重复
            is_duplicate = False
            
            for existing_region in deduplicated:
                existing_text = existing_region.get('text', '').strip()
                existing_bbox = existing_region.get('bbox', [0, 0, 0, 0])
                
                # 文本相似度检查
                text_similarity = self._calculate_text_similarity(current_text, existing_text)
                
                # 位置重叠检查
                overlap_ratio = self._calculate_bbox_overlap(current_bbox, existing_bbox)
                
                # 判断是否为重复
                if (text_similarity > 0.8 and overlap_ratio > 0.3) or \
                   (text_similarity > 0.9) or \
                   (overlap_ratio > 0.7 and text_similarity > 0.5):
                    is_duplicate = True
                    logger.debug(f"检测到重复文本: '{current_text}' vs '{existing_text}', "
                               f"文本相似度: {text_similarity:.2f}, 重叠率: {overlap_ratio:.2f}")
                    break
            
            if not is_duplicate:
                deduplicated.append(current_region)
        
        logger.info(f"去重完成: {len(text_regions)} -> {len(deduplicated)} 个文本区域")
        return deduplicated
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符级相似度计算
        set1 = set(text1)
        set2 = set(text2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_bbox_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
        """计算边界框重叠率"""
        if len(bbox1) != 4 or len(bbox2) != 4:
            return 0.0
        
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # 计算交集
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # 计算并集
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = area1 + area2 - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def _calculate_average_confidence(self, text_regions: List[Dict[str, Any]]) -> float:
        """计算平均置信度"""
        if not text_regions:
            return 0.0
        
        confidences = [region.get('confidence', 0) for region in text_regions]
        return sum(confidences) / len(confidences)
    
    async def _process_direct_ocr(self, 
                                image_path: str, 
                                task_id: str, 
                                save_to_storage: bool) -> MergedOCRResult:
        """直接OCR处理（不切片）"""
        
        logger.info(f"执行直接OCR处理 - {task_id}")
        start_time = time.time()
        
        try:
            # 调用原始OCR服务
            ocr_result = self.ocr_service.recognize_text(
                image_path=image_path,
                save_to_sealos=save_to_storage,
                drawing_id=task_id
            )
            
            processing_time = time.time() - start_time
            
            # 转换为统一格式
            text_regions = ocr_result.get('text_regions', [])
            all_text = ocr_result.get('all_text', '')
            
            # 获取图像信息
            with cv2.imread(image_path) as img:
                height, width = img.shape[:2] if img is not None else (0, 0)
            
            processing_summary = {
                'original_image': {
                    'width': width,
                    'height': height,
                    'total_pixels': width * height
                },
                'slicing_info': {
                    'total_slices': 1,
                    'successful_slices': 1 if ocr_result.get('success', False) else 0,
                    'success_rate': 1.0 if ocr_result.get('success', False) else 0.0,
                    'slice_config': None
                },
                'ocr_statistics': {
                    'total_text_regions_before_dedup': len(text_regions),
                    'total_text_regions_after_dedup': len(text_regions),
                    'deduplication_rate': 0.0,
                    'total_characters': len(all_text),
                    'avg_confidence': self._calculate_average_confidence(text_regions)
                },
                'performance': {
                    'total_processing_time': processing_time,
                    'avg_slice_processing_time': processing_time
                }
            }
            
            # 创建虚拟切片结果
            slice_result = OCRSliceResult(
                slice_id=f"{task_id}_direct",
                slice_index=0,
                slice_bounds=(0, 0, width, height),
                slice_path=image_path,
                ocr_result=ocr_result,
                text_regions=text_regions,
                processing_time=processing_time,
                success=ocr_result.get('success', False)
            )
            
            return MergedOCRResult(
                task_id=task_id,
                total_slices=1,
                successful_slices=1 if ocr_result.get('success', False) else 0,
                success_rate=1.0 if ocr_result.get('success', False) else 0.0,
                total_text_regions=len(text_regions),
                merged_text_regions=text_regions,
                all_text=all_text,
                processing_summary=processing_summary,
                slice_results=[slice_result],
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"直接OCR处理失败 - {task_id}: {e}")
            raise
    
    async def _save_results_to_storage(self, merged_result: MergedOCRResult, task_id: str):
        """保存结果到双重存储"""
        if not self.storage:
            logger.warning("存储服务不可用，跳过结果保存")
            return
            
        try:
            # 保存合并后的OCR结果
            result_data = {
                'task_id': merged_result.task_id,
                'total_text_regions': merged_result.total_text_regions,
                'merged_text_regions': merged_result.merged_text_regions,
                'all_text': merged_result.all_text,
                'processing_summary': merged_result.processing_summary,
                'timestamp': time.time()
            }
            
            # 使用双重存储异步上传
            result_key = f"ocr_slicing_results/{task_id}/merged_result.json"
            url = await self.storage.upload_json_content_async(
                data=result_data,
                file_path=result_key
            )
            
            logger.info(f"✅ OCR切片结果已保存到双重存储: {url}")
            
        except Exception as e:
            logger.error(f"保存OCR切片结果到双重存储失败: {e}")
            # 不抛出异常，因为保存失败不应该影响主要处理流程
    
    async def process_image_async(self, image_path: str, use_slicing: Optional[bool] = None) -> Dict[str, Any]:
        """
        异步处理图像OCR（兼容原始接口）
        
        Args:
            image_path: 图像文件路径
            use_slicing: 兼容性参数，智能切片版本会忽略此参数
            
        Returns:
            OCR结果（兼容原始格式）
        """
        try:
            merged_result = await self.process_image_with_slicing(image_path)
            
            # 转换为兼容格式
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
                'avg_confidence': merged_result.processing_summary['ocr_statistics']['avg_confidence'],
                'processing_time': merged_result.processing_time
            }
            
        except Exception as e:
            logger.error(f"异步OCR处理失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'texts': [],
                'text_regions': [],
                'all_text': '',
                'statistics': {'total_regions': 0, 'avg_confidence': 0, 'processing_time': 0}
            }

# 全局实例
paddle_ocr_with_slicing = PaddleOCRWithSlicing() 