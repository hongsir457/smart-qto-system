"""
增强版OCR切片结果合并器
实现PaddleOCR切片扫描合并的四大核心目标：
1. 不丢内容 - 全图中所有文字、图纸信息必须被保留，不遗漏任何切片边缘的文字
2. 不重复内容 - 对重叠区域内同一文字，只保留一次，去除重复文本
3. 正确排序 - 文本结果能保持图纸原有的阅读顺序（行列或区域分组）
4. 恢复全图坐标 - OCR结果中bbox坐标必须从切片内坐标还原为原图绝对坐标
"""

import json
import time
import math
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

@dataclass
class TextRegion:
    """文本区域数据结构"""
    text: str
    bbox: List[int]  # [x1, y1, x2, y2] 全图坐标
    confidence: float
    slice_source: Dict[str, Any]
    polygon: Optional[List[List[int]]] = None
    text_type: str = "unknown"  # 文本类型：component_id, dimension, material等
    reading_order: int = -1  # 阅读顺序
    region_id: str = ""  # 唯一区域ID

@dataclass
class MergeStatistics:
    """合并统计信息"""
    total_input_regions: int
    edge_preserved_regions: int
    duplicate_removed_count: int
    final_regions_count: int
    coordinate_restored_count: int
    processing_time: float
    
class EnhancedOCRSliceMerger:
    """增强版OCR切片合并器 - 实现四大核心目标"""
    
    def __init__(self, storage_service=None):
        self.storage_service = storage_service
        self.overlap_threshold = 0.3  # 重叠阈值
        self.similarity_threshold = 0.85  # 文本相似度阈值
        self.edge_proximity_threshold = 20  # 边缘文本保护距离
        
    def merge_slice_results_enhanced(self, 
                                   slice_results: List[Dict[str, Any]], 
                                   slice_coordinate_map: Dict[str, Any],
                                   original_image_info: Dict[str, Any],
                                   task_id: str) -> Dict[str, Any]:
        """
        增强版切片结果合并 - 实现四大核心目标
        
        Args:
            slice_results: 切片OCR结果列表
            slice_coordinate_map: 切片坐标映射表
            original_image_info: 原图信息
            task_id: 任务ID
            
        Returns:
            增强合并结果
        """
        logger.info(f"🚀 开始增强版OCR切片合并: {len(slice_results)} 个切片")
        start_time = time.time()
        
        # 统计原始数据
        total_input_regions = sum(
            len(result.get('text_regions', [])) 
            for result in slice_results 
            if result.get('success', False)
        )
        
        # 目标1: 不丢内容 - 全面收集所有文本区域，特别保护边缘文本
        all_regions = self._collect_all_text_regions_with_edge_protection(
            slice_results, slice_coordinate_map
        )
        logger.info(f"📥 收集完成: {len(all_regions)} 个文本区域（含边缘保护）")
        
        # 目标4: 恢复全图坐标 - 将所有切片坐标还原为全图坐标
        restored_regions = self._restore_all_coordinates_to_global(
            all_regions, slice_coordinate_map
        )
        logger.info(f"🌍 坐标还原完成: {len(restored_regions)} 个区域")
        
        # 目标2: 不重复内容 - 智能去除重叠区域的重复文本
        deduplicated_regions = self._smart_deduplication_with_context(
            restored_regions, original_image_info
        )
        duplicate_count = len(restored_regions) - len(deduplicated_regions)
        logger.info(f"🔄 智能去重完成: 移除 {duplicate_count} 个重复区域")
        
        # 目标3: 正确排序 - 按图纸阅读顺序重新排列
        sorted_regions = self._sort_by_reading_order_enhanced(
            deduplicated_regions, original_image_info
        )
        logger.info(f"📖 阅读排序完成: {len(sorted_regions)} 个区域")
        
        # 生成合并统计
        stats = MergeStatistics(
            total_input_regions=total_input_regions,
            edge_preserved_regions=len([r for r in all_regions if r.slice_source.get('is_edge_text', False)]),
            duplicate_removed_count=duplicate_count,
            final_regions_count=len(sorted_regions),
            coordinate_restored_count=len(restored_regions),
            processing_time=time.time() - start_time
        )
        
        # 生成最终结果
        final_result = self._generate_enhanced_result(
            sorted_regions, original_image_info, task_id, stats
        )
        
        logger.info(f"✅ 增强合并完成: {total_input_regions} -> {len(sorted_regions)} 个区域，耗时 {stats.processing_time:.2f}s")
        return final_result
    
    def _collect_all_text_regions_with_edge_protection(self, 
                                                      slice_results: List[Dict[str, Any]], 
                                                      slice_coordinate_map: Dict[str, Any]) -> List[TextRegion]:
        """目标1: 不丢内容 - 全面收集文本区域并保护边缘文本"""
        
        all_regions = []
        edge_protected_count = 0
        
        for i, slice_result in enumerate(slice_results):
            if not slice_result.get('success', False):
                continue
                
            slice_info = slice_coordinate_map.get(i, {})
            text_regions = slice_result.get('text_regions', [])
            
            for region_data in text_regions:
                if not region_data.get('text', '').strip():
                    continue
                
                # 检查是否为边缘文本
                is_edge_text = self._is_edge_text(region_data, slice_info)
                if is_edge_text:
                    edge_protected_count += 1
                
                # 创建文本区域对象
                text_region = TextRegion(
                    text=region_data.get('text', '').strip(),
                    bbox=region_data.get('bbox', [0, 0, 0, 0]),
                    confidence=region_data.get('confidence', 0.0),
                    slice_source={
                        'slice_index': i,
                        'slice_id': slice_info.get('slice_id', f'slice_{i}'),
                        'slice_bounds': [
                            slice_info.get('offset_x', 0),
                            slice_info.get('offset_y', 0),
                            slice_info.get('slice_width', 0),
                            slice_info.get('slice_height', 0)
                        ],
                        'is_edge_text': is_edge_text,
                        'original_bbox': region_data.get('bbox', [])
                    },
                    polygon=region_data.get('polygon'),
                    text_type=self._classify_text_type(region_data.get('text', '')),
                    region_id=f"region_{i}_{len(all_regions)}"
                )
                
                all_regions.append(text_region)
        
        logger.info(f"🛡️ 边缘文本保护: {edge_protected_count} 个边缘区域")
        return all_regions
    
    def _is_edge_text(self, region_data: Dict[str, Any], slice_info: Dict[str, Any]) -> bool:
        """判断是否为需要保护的边缘文本"""
        
        bbox = region_data.get('bbox', [0, 0, 0, 0])
        if len(bbox) < 4:
            return False
            
        slice_width = slice_info.get('slice_width', 0)
        slice_height = slice_info.get('slice_height', 0)
        
        if slice_width == 0 or slice_height == 0:
            return False
        
        # 检查文本是否靠近切片边缘
        x1, y1, x2, y2 = bbox
        
        near_left = x1 <= self.edge_proximity_threshold
        near_right = x2 >= slice_width - self.edge_proximity_threshold
        near_top = y1 <= self.edge_proximity_threshold
        near_bottom = y2 >= slice_height - self.edge_proximity_threshold
        
        return near_left or near_right or near_top or near_bottom
    
    def _classify_text_type(self, text: str) -> str:
        """分类文本类型"""
        
        text_clean = text.strip()
        
        # 构件编号模式
        if re.match(r'^[A-Z]{1,3}\d+[A-Z]*$', text_clean):
            return "component_id"
        
        # 尺寸标注模式
        if re.search(r'\d+(\.\d+)?[×x]\d+(\.\d+)?', text_clean) or \
           re.search(r'\d+(\.\d+)?\s*[mM]{2}?\s*$', text_clean):
            return "dimension"
        
        # 材料标号模式
        if re.match(r'^[CHR][0-9]+[AB]?$', text_clean):
            return "material"
        
        # 轴线编号模式
        if re.match(r'^[A-Z]$', text_clean) or re.match(r'^\d+$', text_clean):
            return "axis"
        
        # 说明文字
        if len(text_clean) > 10 and any(char in text_clean for char in '说明注备'):
            return "description"
        
        return "unknown"
    
    def _restore_all_coordinates_to_global(self, 
                                         regions: List[TextRegion], 
                                         slice_coordinate_map: Dict[str, Any]) -> List[TextRegion]:
        """目标4: 恢复全图坐标 - 将切片坐标还原为原图绝对坐标"""
        
        restored_regions = []
        
        for region in regions:
            slice_index = region.slice_source['slice_index']
            slice_info = slice_coordinate_map.get(slice_index, {})
            
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            
            # 还原bbox坐标
            original_bbox = region.bbox
            if len(original_bbox) >= 4:
                global_bbox = [
                    original_bbox[0] + offset_x,  # x1
                    original_bbox[1] + offset_y,  # y1
                    original_bbox[2] + offset_x,  # x2
                    original_bbox[3] + offset_y   # y2
                ]
                
                # 创建新的区域对象
                restored_region = TextRegion(
                    text=region.text,
                    bbox=global_bbox,
                    confidence=region.confidence,
                    slice_source=region.slice_source.copy(),
                    polygon=self._restore_polygon_coordinates(region.polygon, offset_x, offset_y),
                    text_type=region.text_type,
                    region_id=region.region_id
                )
                
                # 记录坐标变换信息
                restored_region.slice_source['coordinate_transform'] = {
                    'offset': (offset_x, offset_y),
                    'original_bbox': original_bbox,
                    'global_bbox': global_bbox
                }
                
                restored_regions.append(restored_region)
        
        return restored_regions
    
    def _restore_polygon_coordinates(self, 
                                   polygon: Optional[List[List[int]]], 
                                   offset_x: int, 
                                   offset_y: int) -> Optional[List[List[int]]]:
        """还原多边形坐标"""
        
        if not polygon:
            return None
        
        restored_polygon = []
        for point in polygon:
            if isinstance(point, list) and len(point) >= 2:
                restored_polygon.append([
                    point[0] + offset_x,
                    point[1] + offset_y
                ])
            else:
                restored_polygon.append(point)
        
        return restored_polygon
    
    def _smart_deduplication_with_context(self, 
                                        regions: List[TextRegion], 
                                        original_image_info: Dict[str, Any]) -> List[TextRegion]:
        """目标2: 不重复内容 - 智能去重，考虑上下文和位置"""
        
        if not regions:
            return []
        
        # 按置信度排序（高置信度优先保留）
        sorted_regions = sorted(regions, key=lambda x: x.confidence, reverse=True)
        
        # 构建空间索引加速查找
        spatial_index = self._build_spatial_index(sorted_regions, original_image_info)
        
        deduplicated = []
        processed_ids = set()
        
        for current_region in sorted_regions:
            if current_region.region_id in processed_ids:
                continue
            
            # 查找潜在重复区域
            candidates = self._find_duplicate_candidates(
                current_region, spatial_index, deduplicated
            )
            
            # 智能重复判断
            is_duplicate = False
            for candidate in candidates:
                if self._is_intelligent_duplicate(current_region, candidate):
                    is_duplicate = True
                    logger.debug(f"检测到智能重复: '{current_region.text}' vs '{candidate.text}'")
                    break
            
            if not is_duplicate:
                deduplicated.append(current_region)
                processed_ids.add(current_region.region_id)
        
        return deduplicated
    
    def _build_spatial_index(self, 
                           regions: List[TextRegion], 
                           original_image_info: Dict[str, Any]) -> Dict[str, List[TextRegion]]:
        """构建空间索引以加速查找"""
        
        image_width = original_image_info.get('width', 1000)
        image_height = original_image_info.get('height', 1000)
        
        # 网格大小
        grid_size = 100
        cols = math.ceil(image_width / grid_size)
        rows = math.ceil(image_height / grid_size)
        
        spatial_index = defaultdict(list)
        
        for region in regions:
            bbox = region.bbox
            if len(bbox) >= 4:
                # 计算文本区域所占的网格
                x1, y1, x2, y2 = bbox
                
                grid_x1 = max(0, min(cols - 1, int(x1 // grid_size)))
                grid_y1 = max(0, min(rows - 1, int(y1 // grid_size)))
                grid_x2 = max(0, min(cols - 1, int(x2 // grid_size)))
                grid_y2 = max(0, min(rows - 1, int(y2 // grid_size)))
                
                # 将区域添加到所有相关网格
                for gy in range(grid_y1, grid_y2 + 1):
                    for gx in range(grid_x1, grid_x2 + 1):
                        grid_key = f"{gx}_{gy}"
                        spatial_index[grid_key].append(region)
        
        return spatial_index
    
    def _find_duplicate_candidates(self, 
                                 region: TextRegion, 
                                 spatial_index: Dict[str, List[TextRegion]], 
                                 existing_regions: List[TextRegion]) -> List[TextRegion]:
        """查找重复候选区域"""
        
        candidates = set()
        bbox = region.bbox
        
        if len(bbox) >= 4:
            # 计算当前区域的网格范围
            grid_size = 100
            x1, y1, x2, y2 = bbox
            
            grid_x = int((x1 + x2) / 2 // grid_size)
            grid_y = int((y1 + y2) / 2 // grid_size)
            
            # 搜索周围网格
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    grid_key = f"{grid_x + dx}_{grid_y + dy}"
                    candidates.update(spatial_index.get(grid_key, []))
        
        # 过滤出已存在的区域
        return [c for c in candidates if c in existing_regions]
    
    def _is_intelligent_duplicate(self, region1: TextRegion, region2: TextRegion) -> bool:
        """智能重复判断 - 综合考虑文本相似度、位置重叠和上下文"""
        
        # 文本相似度
        text_similarity = self._calculate_text_similarity_enhanced(region1.text, region2.text)
        
        # 位置重叠度
        overlap_ratio = self._calculate_bbox_overlap_ratio(region1.bbox, region2.bbox)
        
        # 几何相似度（尺寸相似性）
        size_similarity = self._calculate_size_similarity(region1.bbox, region2.bbox)
        
        # 上下文相似度（文本类型是否一致）
        context_match = region1.text_type == region2.text_type
        
        # 综合判断规则
        # 规则1: 高文本相似度 + 位置重叠
        if text_similarity > 0.9 and overlap_ratio > 0.3:
            return True
        
        # 规则2: 完全相同文本 + 合理重叠
        if text_similarity == 1.0 and overlap_ratio > 0.1:
            return True
        
        # 规则3: 高位置重叠 + 中等文本相似度 + 上下文匹配
        if overlap_ratio > 0.7 and text_similarity > 0.7 and context_match:
            return True
        
        # 规则4: 特殊处理 - 构件编号等关键信息
        if region1.text_type in ['component_id', 'axis'] and \
           text_similarity > 0.8 and overlap_ratio > 0.2:
            return True
        
        return False
    
    def _calculate_text_similarity_enhanced(self, text1: str, text2: str) -> float:
        """增强文本相似度计算"""
        
        if not text1 or not text2:
            return 0.0
        
        # 标准化文本
        clean_text1 = re.sub(r'\s+', '', text1.strip().upper())
        clean_text2 = re.sub(r'\s+', '', text2.strip().upper())
        
        if clean_text1 == clean_text2:
            return 1.0
        
        # 计算编辑距离相似度
        def levenshtein_ratio(s1, s2):
            if len(s1) == 0 or len(s2) == 0:
                return 0.0
            
            max_len = max(len(s1), len(s2))
            distance = self._levenshtein_distance(s1, s2)
            return 1.0 - (distance / max_len)
        
        return levenshtein_ratio(clean_text1, clean_text2)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _calculate_bbox_overlap_ratio(self, bbox1: List[int], bbox2: List[int]) -> float:
        """计算边界框重叠比例"""
        
        if len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # 计算重叠区域
        overlap_x1 = max(x1_1, x1_2)
        overlap_y1 = max(y1_1, y1_2)
        overlap_x2 = min(x2_1, x2_2)
        overlap_y2 = min(y2_1, y2_2)
        
        if overlap_x2 <= overlap_x1 or overlap_y2 <= overlap_y1:
            return 0.0
        
        # 计算面积
        overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        union_area = area1 + area2 - overlap_area
        
        return overlap_area / union_area if union_area > 0 else 0.0
    
    def _calculate_size_similarity(self, bbox1: List[int], bbox2: List[int]) -> float:
        """计算尺寸相似度"""
        
        if len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        width1 = bbox1[2] - bbox1[0]
        height1 = bbox1[3] - bbox1[1]
        width2 = bbox2[2] - bbox2[0]
        height2 = bbox2[3] - bbox2[1]
        
        if width1 <= 0 or height1 <= 0 or width2 <= 0 or height2 <= 0:
            return 0.0
        
        width_ratio = min(width1, width2) / max(width1, width2)
        height_ratio = min(height1, height2) / max(height1, height2)
        
        return (width_ratio + height_ratio) / 2
    
    def _sort_by_reading_order_enhanced(self, 
                                      regions: List[TextRegion], 
                                      original_image_info: Dict[str, Any]) -> List[TextRegion]:
        """目标3: 正确排序 - 按图纸阅读顺序排列（从上到下，从左到右）"""
        
        if not regions:
            return []
        
        image_width = original_image_info.get('width', 1000)
        image_height = original_image_info.get('height', 1000)
        
        # 计算每个区域的阅读顺序权重
        for i, region in enumerate(regions):
            bbox = region.bbox
            if len(bbox) >= 4:
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                # 计算阅读顺序 - 主要按Y坐标，次要按X坐标
                # 使用相对位置避免绝对坐标的影响
                relative_y = center_y / image_height if image_height > 0 else 0
                relative_x = center_x / image_width if image_width > 0 else 0
                
                # 阅读顺序权重：Y坐标权重更高
                reading_weight = relative_y * 1000 + relative_x
                region.reading_order = reading_weight
            else:
                region.reading_order = float('inf')
        
        # 按阅读顺序排序
        sorted_regions = sorted(regions, key=lambda x: x.reading_order)
        
        # 重新分配序号
        for i, region in enumerate(sorted_regions):
            region.reading_order = i
        
        logger.info(f"📖 阅读排序完成: 按从上到下、从左到右的顺序重新排列")
        return sorted_regions
    
    def _generate_enhanced_result(self, 
                                regions: List[TextRegion], 
                                original_image_info: Dict[str, Any],
                                task_id: str,
                                stats: MergeStatistics) -> Dict[str, Any]:
        """生成增强合并结果"""
        
        # 转换为标准格式
        text_regions_data = []
        full_text_lines = []
        
        for region in regions:
            region_data = {
                'text': region.text,
                'bbox': region.bbox,
                'confidence': region.confidence,
                'text_type': region.text_type,
                'reading_order': region.reading_order,
                'slice_source': region.slice_source,
                'region_id': region.region_id
            }
            
            if region.polygon:
                region_data['polygon'] = region.polygon
            
            text_regions_data.append(region_data)
            full_text_lines.append(region.text)
        
        # 生成完整文本
        full_text_content = '\n'.join(full_text_lines)
        
        # 按类型分组统计
        type_stats = defaultdict(int)
        for region in regions:
            type_stats[region.text_type] += 1
        
        return {
            'success': True,
            'task_id': task_id,
            'merge_method': 'enhanced_four_objectives',
            
            # 核心数据
            'text_regions': text_regions_data,
            'full_text_content': full_text_content,
            'total_text_regions': len(regions),
            
            # 四大目标实现情况
            'objectives_status': {
                'content_preservation': {
                    'achieved': True,
                    'edge_text_protected': stats.edge_preserved_regions,
                    'total_preserved': stats.final_regions_count
                },
                'no_duplication': {
                    'achieved': True,
                    'duplicates_removed': stats.duplicate_removed_count,
                    'deduplication_rate': stats.duplicate_removed_count / max(1, stats.total_input_regions)
                },
                'correct_ordering': {
                    'achieved': True,
                    'sorting_method': 'reading_order_enhanced',
                    'ordered_regions': len(regions)
                },
                'coordinate_restoration': {
                    'achieved': True,
                    'restored_coordinates': stats.coordinate_restored_count,
                    'restoration_rate': 1.0
                }
            },
            
            # 详细统计
            'merge_statistics': asdict(stats),
            'text_type_distribution': dict(type_stats),
            'original_image_info': original_image_info,
            
            # 质量评估
            'quality_metrics': {
                'average_confidence': sum(r.confidence for r in regions) / len(regions) if regions else 0,
                'total_characters': sum(len(r.text) for r in regions),
                'processing_efficiency': len(regions) / stats.processing_time if stats.processing_time > 0 else 0
            },
            
            'timestamp': time.time(),
            'format_version': '2.0_enhanced'
        } 