#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能图像切片模块
确保上传给OpenAI Vision API时不失真，满足2048x2048分辨率要求
"""

import logging
import base64
import json
import math
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
from dataclasses import dataclass
import asyncio
import aiofiles

from app.core.config import settings
from app.services.sealos_storage import SealosStorage
from app.services.dual_storage_service import DualStorageService
from app.services.s3_service import S3Service

logger = logging.getLogger(__name__)

@dataclass
class SliceInfo:
    """切片信息"""
    slice_id: str
    x: int
    y: int
    width: int
    height: int
    overlap_left: int
    overlap_top: int
    overlap_right: int
    overlap_bottom: int
    base64_data: str
    file_size_kb: float
    slice_path: str

@dataclass
class SliceAnalysisResult:
    """切片分析结果"""
    slice_id: str
    analysis_result: Dict[str, Any]
    components: List[Dict[str, Any]]
    confidence_score: float
    processing_time: float

class IntelligentImageSlicer:
    """智能图像切片器"""
    
    def __init__(self):
        """初始化切片器"""
        self.max_resolution = 2048  # OpenAI API最大分辨率
        self.overlap_ratio = 0.1    # 重叠区域比例 (10%)
        self.min_slice_size = 512   # 最小切片尺寸
        self.quality = 95           # 图像质量
        self.sealos_storage = SealosStorage()
        self.dual_storage = DualStorageService()
        self.s3_service = S3Service()
        
        # 优先使用S3存储，降级到Sealos存储
        self.primary_storage = self.s3_service
        self.fallback_storage = self.sealos_storage
        
    def is_available(self) -> bool:
        """检查智能切片器是否可用"""
        try:
            # 检查PIL库
            test_image = Image.new('RGB', (100, 100), color='red')
            if test_image is None:
                return False
            
            # 检查基本计算功能
            strategy = self.calculate_optimal_slicing(1024, 768)
            if strategy is None:
                return False
            
            return True
        except Exception as e:
            logger.error(f"智能切片器可用性检查失败: {e}")
            return False
        
    def calculate_optimal_slicing(self, image_width: int, image_height: int) -> Dict[str, Any]:
        """
        计算最优切片策略
        
        Args:
            image_width: 图像宽度
            image_height: 图像高度
            
        Returns:
            切片策略信息
        """
        logger.info(f"计算最优切片策略: {image_width}×{image_height}")
        
        # 如果图像已经满足要求，不需要切片
        if image_width <= self.max_resolution and image_height <= self.max_resolution:
            return {
                'need_slicing': False,
                'original_size': (image_width, image_height),
                'slices_count': 1,
                'strategy': 'no_slicing'
            }
        
        # 计算重叠区域大小
        overlap_x = int(self.max_resolution * self.overlap_ratio)
        overlap_y = int(self.max_resolution * self.overlap_ratio)
        
        # 计算有效切片尺寸（减去重叠区域）
        effective_slice_width = self.max_resolution - overlap_x
        effective_slice_height = self.max_resolution - overlap_y
        
        # 计算需要的切片数量
        slices_x = math.ceil(image_width / effective_slice_width)
        slices_y = math.ceil(image_height / effective_slice_height)
        
        # 计算实际切片尺寸
        actual_slice_width = min(self.max_resolution, 
                               (image_width + overlap_x * (slices_x - 1)) // slices_x)
        actual_slice_height = min(self.max_resolution,
                                (image_height + overlap_y * (slices_y - 1)) // slices_y)
        
        strategy_info = {
            'need_slicing': True,
            'original_size': (image_width, image_height),
            'slices_count': slices_x * slices_y,
            'slices_grid': (slices_x, slices_y),
            'slice_size': (actual_slice_width, actual_slice_height),
            'effective_size': (effective_slice_width, effective_slice_height),
            'overlap_size': (overlap_x, overlap_y),
            'strategy': 'intelligent_overlap'
        }
        
        logger.info(f"切片策略: {slices_x}×{slices_y}网格, 切片尺寸: {actual_slice_width}×{actual_slice_height}")
        
        return strategy_info
    
    def slice_image(self, image: Image.Image, task_id: str) -> List[SliceInfo]:
        """
        智能切片图像
        
        Args:
            image: PIL图像对象
            task_id: 任务ID
            
        Returns:
            切片信息列表
        """
        logger.info(f"开始智能切片 - 任务ID: {task_id}")
        
        image_width, image_height = image.size
        strategy = self.calculate_optimal_slicing(image_width, image_height)
        
        slices = []
        
        if not strategy['need_slicing']:
            # 不需要切片，直接处理整张图
            slice_info = self._create_single_slice(image, task_id, "full")
            slices.append(slice_info)
            logger.info("图像尺寸满足要求，无需切片")
            return slices
        
        # 执行智能切片
        slices_x, slices_y = strategy['slices_grid']
        slice_width, slice_height = strategy['slice_size']
        overlap_x, overlap_y = strategy['overlap_size']
        
        for row in range(slices_y):
            for col in range(slices_x):
                slice_info = self._create_slice(
                    image, task_id, row, col, 
                    slices_x, slices_y,
                    slice_width, slice_height,
                    overlap_x, overlap_y
                )
                slices.append(slice_info)
        
        logger.info(f"切片完成: 生成 {len(slices)} 个切片")
        return slices
    
    def _create_single_slice(self, image: Image.Image, task_id: str, suffix: str) -> SliceInfo:
        """创建单个切片（无需切片的情况）"""
        slice_id = f"{task_id}_{suffix}"
        
        # 转换为base64
        base64_data = self._image_to_base64(image)
        file_size_kb = len(base64_data) / 1024
        
        return SliceInfo(
            slice_id=slice_id,
            x=0,
            y=0,
            width=image.width,
            height=image.height,
            overlap_left=0,
            overlap_top=0,
            overlap_right=0,
            overlap_bottom=0,
            base64_data=base64_data,
            file_size_kb=file_size_kb,
            slice_path=""
        )
    
    def _create_slice(self, image: Image.Image, task_id: str, 
                     row: int, col: int, total_cols: int, total_rows: int,
                     slice_width: int, slice_height: int,
                     overlap_x: int, overlap_y: int) -> SliceInfo:
        """创建单个切片"""
        
        # 计算切片位置
        start_x = col * (slice_width - overlap_x)
        start_y = row * (slice_height - overlap_y)
        
        # 确保不超出图像边界
        end_x = min(start_x + slice_width, image.width)
        end_y = min(start_y + slice_height, image.height)
        
        # 如果是边缘切片，调整起始位置确保切片尺寸
        if end_x - start_x < slice_width and col == total_cols - 1:
            start_x = max(0, end_x - slice_width)
        if end_y - start_y < slice_height and row == total_rows - 1:
            start_y = max(0, end_y - slice_height)
        
        # 计算实际重叠区域
        overlap_left = overlap_x if col > 0 else 0
        overlap_top = overlap_y if row > 0 else 0
        overlap_right = overlap_x if col < total_cols - 1 else 0
        overlap_bottom = overlap_y if row < total_rows - 1 else 0
        
        # 裁剪图像
        slice_image = image.crop((start_x, start_y, end_x, end_y))
        
        # 生成切片ID
        slice_id = f"{task_id}_slice_{row:02d}_{col:02d}"
        
        # 转换为base64
        base64_data = self._image_to_base64(slice_image)
        file_size_kb = len(base64_data) / 1024
        
        logger.debug(f"创建切片 {slice_id}: 位置({start_x},{start_y})-({end_x},{end_y}), "
                    f"尺寸{slice_image.width}×{slice_image.height}, 大小{file_size_kb:.1f}KB")
        
        slice_path = ""
        try:
            # 使用正确的S3服务上传
            slice_filename = f"{slice_id}.png"
            slice_image_bytes = base64.b64decode(base64_data)
            
            # 创建一个临时的BytesIO对象来模拟文件
            from io import BytesIO
            file_obj = BytesIO(slice_image_bytes)

            # 调用一个接受文件对象的上传方法 (假设存在于S3Service中)
            # 根据s3_service.py的实现，它有 upload_file 方法
            upload_result = self.s3_service.upload_file(
                file_obj=file_obj,
                file_name=slice_filename,
                content_type='image/png',
                folder=f"slices/{task_id}"
            )
            slice_path = upload_result.get("s3_key")
            
            logger.info(f"✅ 成功上传切片到S3: {slice_path}")
        except Exception as e:
            logger.error(f"❌ 上传切片到S3失败: {e}", exc_info=True)
            # 降级到本地存储
            local_slice_dir = Path(f"temp_slices/{task_id}")
            local_slice_dir.mkdir(parents=True, exist_ok=True)
            slice_path = local_slice_dir / slice_filename
            slice_image.save(slice_path)
            logger.warning(f"⚠️ 已将切片保存到本地备用路径: {slice_path}")
        
        return SliceInfo(
            slice_id=slice_id,
            x=start_x,
            y=start_y,
            width=slice_image.width,
            height=slice_image.height,
            overlap_left=overlap_left,
            overlap_top=overlap_top,
            overlap_right=overlap_right,
            overlap_bottom=overlap_bottom,
            base64_data=base64_data,
            file_size_kb=file_size_kb,
            slice_path=str(slice_path)
        )
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """将图像转换为base64编码"""
        import io
        
        # 确保图像是RGB模式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 保存为字节流
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', quality=self.quality, optimize=True)
        buffer.seek(0)
        
        # 编码为base64
        base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return base64_data
    
    async def _upload_to_cloud_storage(self, file_data: bytes, file_path: str, 
                                      content_type: str = "application/octet-stream") -> str:
        """
        通用云存储上传方法
        优先使用S3存储，失败时降级到Sealos存储，最后降级到本地存储
        
        Args:
            file_data: 文件数据
            file_path: 存储路径
            content_type: 内容类型
            
        Returns:
            文件访问URL
        """
        try:
            # 优先使用S3存储
            url = await self.primary_storage.upload_file(file_data, file_path, content_type)
            logger.debug(f"S3存储上传成功: {file_path} -> {url}")
            return url
        except Exception as e:
            logger.warning(f"S3存储上传失败: {e}, 尝试备用存储")
            
            try:
                # 降级到Sealos存储
                url = await self.fallback_storage.upload_file(file_data, file_path, content_type)
                logger.debug(f"Sealos存储上传成功: {file_path} -> {url}")
                return url
            except Exception as e2:
                logger.error(f"所有云存储都失败: S3({e}), Sealos({e2})")
                raise Exception(f"云存储上传失败: {e2}")

    async def save_slices_to_cloud(self, slices: List[SliceInfo], task_id: str) -> Dict[str, str]:
        """
        保存切片到云存储（支持S3和Sealos）
        
        Args:
            slices: 切片信息列表
            task_id: 任务ID
            
        Returns:
            切片文件URL映射
        """
        logger.info(f"保存 {len(slices)} 个切片到云存储 - 任务ID: {task_id}")
        
        slice_urls = {}
        
        for slice_info in slices:
            try:
                # 构建文件路径
                file_path = f"slices/{task_id}/{slice_info.slice_id}.png"
                
                # 解码base64数据
                image_data = base64.b64decode(slice_info.base64_data)
                
                # 上传到云存储
                url = await self._upload_to_cloud_storage(
                    file_data=image_data,
                    file_path=file_path,
                    content_type="image/png"
                )
                
                slice_urls[slice_info.slice_id] = url
                logger.debug(f"切片 {slice_info.slice_id} 上传成功: {url}")
                
            except Exception as e:
                logger.error(f"上传切片 {slice_info.slice_id} 失败: {e}")
                slice_urls[slice_info.slice_id] = None
        
        # 保存切片元数据
        metadata = {
            'task_id': task_id,
            'total_slices': len(slices),
            'slice_info': [
                {
                    'slice_id': s.slice_id,
                    'position': (s.x, s.y),
                    'size': (s.width, s.height),
                    'overlap': (s.overlap_left, s.overlap_top, s.overlap_right, s.overlap_bottom),
                    'file_size_kb': s.file_size_kb,
                    'url': slice_urls.get(s.slice_id)
                }
                for s in slices
            ]
        }
        
        # 保存元数据到云存储
        metadata_path = f"slices/{task_id}/metadata.json"
        metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
        
        try:
            metadata_url = await self._upload_to_cloud_storage(
                file_data=metadata_json.encode('utf-8'),
                file_path=metadata_path,
                content_type="application/json"
            )
            slice_urls['metadata'] = metadata_url
            logger.info(f"切片元数据保存成功: {metadata_url}")
        except Exception as e:
            logger.error(f"保存切片元数据失败: {e}")
        
        return slice_urls
    
    def merge_analysis_results(self, slice_results: List[SliceAnalysisResult], 
                             original_size: Tuple[int, int],
                             slice_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并切片分析结果
        
        Args:
            slice_results: 切片分析结果列表
            original_size: 原始图像尺寸
            slice_metadata: 切片元数据
            
        Returns:
            合并后的分析结果
        """
        logger.info(f"开始合并 {len(slice_results)} 个切片的分析结果")
        
        merged_components = []
        total_confidence = 0
        total_processing_time = 0
        
        # 创建坐标映射
        slice_positions = {}
        for slice_info in slice_metadata.get('slice_info', []):
            slice_positions[slice_info['slice_id']] = {
                'position': slice_info['position'],
                'size': slice_info['size'],
                'overlap': slice_info['overlap']
            }
        
        # 合并各切片的分析结果
        for result in slice_results:
            slice_id = result.slice_id
            slice_pos = slice_positions.get(slice_id, {})
            
            if not slice_pos:
                logger.warning(f"找不到切片 {slice_id} 的位置信息")
                continue
            
            # 调整坐标到原始图像坐标系
            offset_x, offset_y = slice_pos['position']
            overlap = slice_pos['overlap']
            
            for component in result.components:
                # 调整组件坐标
                adjusted_component = self._adjust_component_coordinates(
                    component, offset_x, offset_y, overlap
                )
                
                # 检查是否与已有组件重复（去重）
                if not self._is_duplicate_component(adjusted_component, merged_components):
                    merged_components.append(adjusted_component)
            
            total_confidence += result.confidence_score
            total_processing_time += result.processing_time
        
        # 计算平均置信度
        avg_confidence = total_confidence / len(slice_results) if slice_results else 0
        
        # 构建最终结果
        merged_result = {
            'task_type': 'merged_slice_analysis',
            'original_size': original_size,
            'total_slices': len(slice_results),
            'components': merged_components,
            'statistics': {
                'total_components': len(merged_components),
                'avg_confidence': avg_confidence,
                'total_processing_time': total_processing_time,
                'components_by_type': self._count_components_by_type(merged_components)
            },
            'quality_metrics': {
                'coverage_ratio': self._calculate_coverage_ratio(merged_components, original_size),
                'overlap_detection_rate': self._calculate_overlap_detection_rate(slice_results),
                'consistency_score': self._calculate_consistency_score(slice_results)
            }
        }
        
        logger.info(f"合并完成: 识别到 {len(merged_components)} 个构件, "
                   f"平均置信度 {avg_confidence:.2f}")
        
        return merged_result
    
    def _adjust_component_coordinates(self, component: Dict[str, Any], 
                                    offset_x: int, offset_y: int,
                                    overlap: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """调整组件坐标到原始图像坐标系"""
        adjusted = component.copy()
        
        # 调整边界框坐标
        if 'bbox' in component:
            bbox = component['bbox']
            adjusted['bbox'] = [
                bbox[0] + offset_x,
                bbox[1] + offset_y,
                bbox[2] + offset_x,
                bbox[3] + offset_y
            ]
        
        # 调整中心点坐标
        if 'center' in component:
            center = component['center']
            adjusted['center'] = [
                center[0] + offset_x,
                center[1] + offset_y
            ]
        
        # 调整多边形坐标
        if 'polygon' in component:
            polygon = component['polygon']
            adjusted['polygon'] = [
                [point[0] + offset_x, point[1] + offset_y]
                for point in polygon
            ]
        
        # 添加切片来源信息
        adjusted['slice_source'] = {
            'offset': (offset_x, offset_y),
            'overlap_region': self._is_in_overlap_region(component, overlap)
        }
        
        return adjusted
    
    def _is_duplicate_component(self, component: Dict[str, Any], 
                              existing_components: List[Dict[str, Any]]) -> bool:
        """检查组件是否重复（在重叠区域）"""
        if 'bbox' not in component:
            return False
        
        bbox1 = component['bbox']
        
        for existing in existing_components:
            if 'bbox' not in existing:
                continue
            
            bbox2 = existing['bbox']
            
            # 计算IoU (Intersection over Union)
            iou = self._calculate_iou(bbox1, bbox2)
            
            # 如果IoU > 0.5，认为是重复组件
            if iou > 0.5:
                # 比较置信度，保留置信度更高的
                conf1 = component.get('confidence', 0)
                conf2 = existing.get('confidence', 0)
                
                if conf1 <= conf2:
                    return True  # 当前组件置信度更低，认为是重复
        
        return False
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个边界框的IoU"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        # 计算交集
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max <= inter_x_min or inter_y_max <= inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        
        # 计算并集
        area1 = (x1_max - x1_min) * (y1_max - y1_min)
        area2 = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def _is_in_overlap_region(self, component: Dict[str, Any], 
                            overlap: Tuple[int, int, int, int]) -> bool:
        """判断组件是否在重叠区域"""
        if 'bbox' not in component:
            return False
        
        bbox = component['bbox']
        overlap_left, overlap_top, overlap_right, overlap_bottom = overlap
        
        # 简化判断：如果组件中心在重叠区域，认为是重叠区域组件
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        return (center_x < overlap_left or center_x > (2048 - overlap_right) or
                center_y < overlap_top or center_y > (2048 - overlap_bottom))
    
    def _count_components_by_type(self, components: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计各类型构件数量"""
        type_counts = {}
        
        for component in components:
            comp_type = component.get('type', 'unknown')
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        
        return type_counts
    
    def _calculate_coverage_ratio(self, components: List[Dict[str, Any]], 
                                original_size: Tuple[int, int]) -> float:
        """计算构件覆盖率"""
        if not components:
            return 0.0
        
        total_area = original_size[0] * original_size[1]
        covered_area = 0
        
        for component in components:
            if 'bbox' in component:
                bbox = component['bbox']
                area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                covered_area += area
        
        return min(covered_area / total_area, 1.0)
    
    def _calculate_overlap_detection_rate(self, slice_results: List[SliceAnalysisResult]) -> float:
        """计算重叠区域检测率"""
        if len(slice_results) <= 1:
            return 1.0
        
        # 简化计算：基于切片数量和平均置信度
        avg_confidence = sum(r.confidence_score for r in slice_results) / len(slice_results)
        return avg_confidence
    
    def _calculate_consistency_score(self, slice_results: List[SliceAnalysisResult]) -> float:
        """计算分析结果一致性得分"""
        if len(slice_results) <= 1:
            return 1.0
        
        # 计算置信度方差作为一致性指标
        confidences = [r.confidence_score for r in slice_results]
        mean_conf = sum(confidences) / len(confidences)
        variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)
        
        # 方差越小，一致性越高
        consistency = max(0, 1 - variance)
        return consistency
    
    async def save_merged_result_to_sealos(self, merged_result: Dict[str, Any], 
                                         task_id: str) -> str:
        """
        保存合并结果到Sealos
        
        Args:
            merged_result: 合并后的分析结果
            task_id: 任务ID
            
        Returns:
            结果文件URL
        """
        try:
            # 构建文件路径
            result_path = f"analysis_results/{task_id}/merged_result.json"
            
            # 序列化结果
            result_json = json.dumps(merged_result, indent=2, ensure_ascii=False)
            
            # 上传到Sealos
            url = await self.storage.upload_file(
                file_data=result_json.encode('utf-8'),
                file_path=result_path,
                content_type="application/json"
            )
            
            logger.info(f"合并结果保存成功: {url}")
            return url
            
        except Exception as e:
            logger.error(f"保存合并结果失败: {e}")
            raise
    
    async def process_image_with_slicing(self, image_path: str, task_id: str) -> Dict[str, Any]:
        """
        完整的图像切片处理流程
        
        Args:
            image_path: 图像文件路径
            task_id: 任务ID
            
        Returns:
            处理结果
        """
        logger.info(f"开始图像切片处理流程 - 任务ID: {task_id}")
        
        try:
            # 1. 加载图像
            image = Image.open(image_path)
            original_size = image.size
            
            # 2. 智能切片
            slices = self.slice_image(image, task_id)
            
            # 3. 保存切片到Sealos
            slice_urls = await self.save_slices_to_cloud(slices, task_id)
            
            # 4. 构建处理结果
            result = {
                'task_id': task_id,
                'original_size': original_size,
                'total_slices': len(slices),
                'slice_urls': slice_urls,
                'slices_info': [
                    {
                        'slice_id': s.slice_id,
                        'position': (s.x, s.y),
                        'size': (s.width, s.height),
                        'file_size_kb': s.file_size_kb,
                        'url': slice_urls.get(s.slice_id)
                    }
                    for s in slices
                ],
                'ready_for_analysis': True
            }
            
            logger.info(f"图像切片处理完成 - 生成 {len(slices)} 个切片")
            return result
            
        except Exception as e:
            logger.error(f"图像切片处理失败: {e}")
            raise
    
    # 保持原有方法向后兼容
    async def save_slices_to_sealos(self, slices: List[SliceInfo], task_id: str) -> Dict[str, str]:
        """
        保存切片到Sealos云存储（向后兼容方法）
        现在内部调用通用云存储方法
        
        Args:
            slices: 切片信息列表
            task_id: 任务ID
            
        Returns:
            切片文件URL映射
        """
        logger.info(f"调用向后兼容的Sealos存储方法，重定向到云存储")
        return await self.save_slices_to_cloud(slices, task_id) 