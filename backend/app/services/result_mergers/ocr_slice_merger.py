"""
OCR切片结果合并器
用于将所有切片的OCR结果合并回原图坐标系，生成统一的全图OCR结果
"""

import json
import time
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class OCRFullResult:
    """全图OCR合并结果"""
    task_id: str
    original_image_info: Dict[str, Any]
    total_slices: int
    successful_slices: int
    success_rate: float
    
    # 合并后的文本内容
    all_text_regions: List[Dict[str, Any]]  # 所有文本区域（已还原坐标）
    full_text_content: str  # 按位置排序的完整文本
    text_by_position: List[Dict[str, Any]]  # 按位置分区的文本
    
    # 统计信息
    total_text_regions: int
    total_characters: int
    average_confidence: float
    
    # 处理信息
    processing_summary: Dict[str, Any]
    merge_metadata: Dict[str, Any]
    timestamp: float

class OCRSliceMerger:
    """OCR切片结果合并器"""
    
    def __init__(self, storage_service=None):
        self.storage_service = storage_service
    
    def merge_slice_results(self, 
                          slice_results: List[Dict[str, Any]], 
                          slice_coordinate_map: Dict[str, Any],
                          original_image_info: Dict[str, Any],
                          task_id: str) -> OCRFullResult:
        """
        合并所有切片的OCR结果
        
        Args:
            slice_results: 切片OCR结果列表
            slice_coordinate_map: 切片坐标映射表
            original_image_info: 原图信息
            task_id: 任务ID
            
        Returns:
            合并后的全图OCR结果
        """
        logger.info(f"🔄 开始合并OCR切片结果: {len(slice_results)} 个切片")
        start_time = time.time()
        
        # 1. 还原所有文本区域坐标到原图坐标系
        all_text_regions = []
        successful_slices = 0
        
        for i, slice_result in enumerate(slice_results):
            if not slice_result.get('success', False):
                continue
                
            successful_slices += 1
            slice_info = slice_coordinate_map.get(i, {})
            
            # 获取切片偏移量
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            
            # 处理该切片的所有文本区域
            text_regions = slice_result.get('text_regions', [])
            for region in text_regions:
                restored_region = self._restore_text_region_coordinates(
                    region, offset_x, offset_y, slice_info, i
                )
                if restored_region:
                    all_text_regions.append(restored_region)
        
        # 2. 去除重叠区域的重复文本
        deduplicated_regions = self._remove_overlapping_duplicates(all_text_regions)
        
        # 3. 按位置排序和分组
        positioned_text = self._organize_text_by_position(
            deduplicated_regions, original_image_info
        )
        
        # 4. 生成完整文本内容
        full_text_content = self._generate_full_text_content(positioned_text)
        
        # 5. 计算统计信息
        stats = self._calculate_statistics(deduplicated_regions)
        
        # 6. 生成处理摘要
        processing_summary = self._generate_processing_summary(
            slice_results, successful_slices, stats, start_time
        )
        
        # 7. 创建合并结果
        ocr_full_result = OCRFullResult(
            task_id=task_id,
            original_image_info=original_image_info,
            total_slices=len(slice_results),
            successful_slices=successful_slices,
            success_rate=successful_slices / len(slice_results) if slice_results else 0,
            
            all_text_regions=deduplicated_regions,
            full_text_content=full_text_content,
            text_by_position=positioned_text,
            
            total_text_regions=len(deduplicated_regions),
            total_characters=stats['total_characters'],
            average_confidence=stats['average_confidence'],
            
            processing_summary=processing_summary,
            merge_metadata={
                'merge_strategy': 'position_and_box_based',
                'coordinate_restoration': True,
                'duplicate_removal': True,
                'position_organization': True,
                'slices_processed': len(slice_results),
                'merge_time': time.time() - start_time
            },
            timestamp=time.time()
        )
        
        logger.info(f"✅ OCR切片合并完成: {len(all_text_regions)} -> {len(deduplicated_regions)} 个文本区域")
        return ocr_full_result
    
    def _restore_text_region_coordinates(self, 
                                       region: Dict[str, Any], 
                                       offset_x: int, 
                                       offset_y: int,
                                       slice_info: Dict[str, Any],
                                       slice_index: int) -> Optional[Dict[str, Any]]:
        """还原文本区域坐标到原图坐标系"""
        
        if not region or not region.get('text', '').strip():
            return None
            
        restored_region = region.copy()
        
        # 还原边界框坐标
        if 'bbox' in region:
            bbox = region['bbox']
            if isinstance(bbox, list) and len(bbox) >= 4:
                restored_region['bbox'] = [
                    bbox[0] + offset_x,  # x1
                    bbox[1] + offset_y,  # y1
                    bbox[2] + offset_x,  # x2
                    bbox[3] + offset_y   # y2
                ]
        
        # 还原多边形坐标（如果有）
        if 'polygon' in region:
            polygon = region['polygon']
            if isinstance(polygon, list):
                restored_polygon = []
                for point in polygon:
                    if isinstance(point, list) and len(point) >= 2:
                        restored_polygon.append([
                            point[0] + offset_x,
                            point[1] + offset_y
                        ])
                    else:
                        restored_polygon.append(point)
                restored_region['polygon'] = restored_polygon
        
        # 添加切片来源信息
        restored_region['slice_source'] = {
            'slice_index': slice_index,
            'slice_id': slice_info.get('slice_id', f'slice_{slice_index}'),
            'offset': (offset_x, offset_y),
            'slice_bounds': (
                slice_info.get('offset_x', 0),
                slice_info.get('offset_y', 0),
                slice_info.get('slice_width', 0),
                slice_info.get('slice_height', 0)
            ),
            'original_bbox': region.get('bbox'),
            'original_polygon': region.get('polygon')
        }
        
        return restored_region
    
    def _remove_overlapping_duplicates(self, text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重叠区域的重复文本"""
        
        if not text_regions:
            return []
        
        logger.info(f"🔄 开始去重: {len(text_regions)} 个文本区域")
        
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
                               f"相似度: {text_similarity:.2f}, 重叠率: {overlap_ratio:.2f}")
                    break
            
            if not is_duplicate:
                deduplicated.append(current_region)
        
        logger.info(f"✅ 去重完成: {len(text_regions)} -> {len(deduplicated)} 个文本区域")
        return deduplicated
    
    def _organize_text_by_position(self, 
                                 text_regions: List[Dict[str, Any]], 
                                 original_image_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按位置组织文本"""
        
        image_width = original_image_info.get('width', 0)
        image_height = original_image_info.get('height', 0)
        
        # 将图像分成网格区域进行位置分组
        grid_rows = 10
        grid_cols = 10
        
        positioned_text = []
        
        for region in text_regions:
            bbox = region.get('bbox', [0, 0, 0, 0])
            if len(bbox) >= 4:
                # 计算文本中心点
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2
                
                # 计算所在网格
                grid_x = int(center_x / image_width * grid_cols) if image_width > 0 else 0
                grid_y = int(center_y / image_height * grid_rows) if image_height > 0 else 0
                
                positioned_region = region.copy()
                positioned_region['position_info'] = {
                    'center': (center_x, center_y),
                    'grid': (grid_x, grid_y),
                    'relative_position': (
                        center_x / image_width if image_width > 0 else 0,
                        center_y / image_height if image_height > 0 else 0
                    )
                }
                
                positioned_text.append(positioned_region)
        
        # 按位置排序（从上到下，从左到右）
        positioned_text.sort(key=lambda x: (
            x['position_info']['grid'][1],  # Y网格优先
            x['position_info']['grid'][0]   # 然后X网格
        ))
        
        return positioned_text
    
    def _generate_full_text_content(self, positioned_text: List[Dict[str, Any]]) -> str:
        """生成完整的文本内容"""
        
        if not positioned_text:
            return ""
        
        # 按行分组
        lines = {}
        for region in positioned_text:
            grid_y = region['position_info']['grid'][1]
            if grid_y not in lines:
                lines[grid_y] = []
            lines[grid_y].append(region)
        
        # 生成文本
        full_text_lines = []
        for y in sorted(lines.keys()):
            line_regions = sorted(lines[y], key=lambda x: x['position_info']['grid'][0])
            line_text = ' '.join(region.get('text', '').strip() for region in line_regions)
            if line_text.strip():
                full_text_lines.append(line_text.strip())
        
        return '\n'.join(full_text_lines)
    
    def _calculate_statistics(self, text_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算统计信息"""
        
        if not text_regions:
            return {
                'total_characters': 0,
                'average_confidence': 0.0,
                'confidence_distribution': {},
                'text_length_distribution': {}
            }
        
        total_characters = sum(len(region.get('text', '')) for region in text_regions)
        confidences = [region.get('confidence', 0) for region in text_regions]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # 置信度分布
        confidence_ranges = {'high': 0, 'medium': 0, 'low': 0}
        for conf in confidences:
            if conf >= 0.8:
                confidence_ranges['high'] += 1
            elif conf >= 0.5:
                confidence_ranges['medium'] += 1
            else:
                confidence_ranges['low'] += 1
        
        # 文本长度分布
        text_lengths = [len(region.get('text', '')) for region in text_regions]
        length_ranges = {'short': 0, 'medium': 0, 'long': 0}
        for length in text_lengths:
            if length <= 5:
                length_ranges['short'] += 1
            elif length <= 20:
                length_ranges['medium'] += 1
            else:
                length_ranges['long'] += 1
        
        return {
            'total_characters': total_characters,
            'average_confidence': average_confidence,
            'confidence_distribution': confidence_ranges,
            'text_length_distribution': length_ranges,
            'max_confidence': max(confidences) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0
        }
    
    def _generate_processing_summary(self, 
                                   slice_results: List[Dict[str, Any]], 
                                   successful_slices: int, 
                                   stats: Dict[str, Any], 
                                   start_time: float) -> Dict[str, Any]:
        """生成处理摘要"""
        
        processing_time = time.time() - start_time
        
        return {
            'slice_processing': {
                'total_slices': len(slice_results),
                'successful_slices': successful_slices,
                'success_rate': successful_slices / len(slice_results) if slice_results else 0,
                'failed_slices': len(slice_results) - successful_slices
            },
            'text_extraction': {
                'total_text_regions_raw': sum(len(r.get('text_regions', [])) for r in slice_results if r.get('success')),
                'final_text_regions': stats.get('total_characters', 0),
                'deduplication_rate': 1 - (stats.get('total_characters', 0) / max(1, sum(len(r.get('text_regions', [])) for r in slice_results if r.get('success'))))
            },
            'quality_metrics': stats,
            'performance': {
                'total_merge_time': processing_time,
                'avg_slice_processing_time': processing_time / len(slice_results) if slice_results else 0
            },
            'merge_strategy': {
                'coordinate_restoration': True,
                'duplicate_removal': True,
                'position_based_organization': True,
                'grid_based_sorting': True
            }
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符级相似度计算
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
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
    
    async def save_ocr_full_result(self, 
                                 ocr_full_result: OCRFullResult, 
                                 drawing_id: int) -> Dict[str, Any]:
        """保存OCR全图合并结果到存储"""
        
        if not self.storage_service:
            logger.warning("存储服务不可用，跳过OCR全图结果保存")
            return {"error": "Storage service not available"}
        
        try:
            # 将结果转换为可序列化的字典
            result_data = {
                'task_id': ocr_full_result.task_id,
                'original_image_info': ocr_full_result.original_image_info,
                'total_slices': ocr_full_result.total_slices,
                'successful_slices': ocr_full_result.successful_slices,
                'success_rate': ocr_full_result.success_rate,
                
                'all_text_regions': ocr_full_result.all_text_regions,
                'full_text_content': ocr_full_result.full_text_content,
                'text_by_position': ocr_full_result.text_by_position,
                
                'total_text_regions': ocr_full_result.total_text_regions,
                'total_characters': ocr_full_result.total_characters,
                'average_confidence': ocr_full_result.average_confidence,
                
                'processing_summary': ocr_full_result.processing_summary,
                'merge_metadata': ocr_full_result.merge_metadata,
                'timestamp': ocr_full_result.timestamp,
                
                'format_version': '1.0',
                'generated_by': 'OCRSliceMerger'
            }
            
            # 保存到存储
            s3_key = f"ocr_results/{drawing_id}/ocr_full.json"
            result_upload = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key,
                content_type="application/json"
            )
            
            if result_upload.get("success"):
                logger.info(f"✅ OCR全图合并结果已保存: {result_upload.get('final_url')}")
                return {
                    "success": True,
                    "s3_url": result_upload.get("final_url"),
                    "s3_key": s3_key,
                    "storage_method": result_upload.get("storage_method")
                }
            else:
                logger.error(f"保存OCR全图合并结果失败: {result_upload.get('error')}")
                return {"success": False, "error": result_upload.get('error')}
            
        except Exception as e:
            logger.error(f"保存OCR全图合并结果异常: {e}")
            return {"success": False, "error": str(e)} 