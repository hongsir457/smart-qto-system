#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VisionScannerService 改进建议完整实现方案
提升准确性和可维护性的四大核心改进
"""

import json
import time
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np

logger = logging.getLogger(__name__)

# ============================================================================
# 改进1: 精确位置匹配 - 替代 round-robin 匹配
# ============================================================================

class PrecisePositionMatcher:
    """精确位置匹配器"""
    
    def __init__(self):
        self.matching_tolerance = 10  # 像素容差
    
    def match_component_to_slice(self, component: Dict[str, Any], 
                               slice_coordinate_map: Dict[str, Any]) -> Optional[str]:
        """
        根据构件的bbox坐标精确匹配对应的切片
        
        Args:
            component: 构件信息，必须包含bbox或position
            slice_coordinate_map: 切片坐标映射
            
        Returns:
            匹配的切片ID，如果无法匹配则返回None
        """
        # 获取构件中心点
        center_point = self._extract_component_center(component)
        if not center_point:
            logger.warning(f"⚠️ 构件缺少有效位置信息: {component.get('component_id', 'unknown')}")
            return None
        
        # 查找包含该中心点的切片
        for slice_id, slice_info in slice_coordinate_map.items():
            if self._point_in_slice(center_point, slice_info):
                logger.debug(f"🎯 构件 {component.get('component_id')} 匹配到切片 {slice_id}")
                return slice_id
        
        logger.warning(f"⚠️ 构件中心点 {center_point} 未找到匹配的切片")
        return None
    
    def _extract_component_center(self, component: Dict[str, Any]) -> Optional[Tuple[float, float]]:
        """提取构件中心点"""
        # 方法1: 从bbox计算中心点
        bbox = component.get('bbox')
        if bbox and len(bbox) >= 4:
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            return (center_x, center_y)
        
        # 方法2: 从position直接获取
        position = component.get('position')
        if position:
            if isinstance(position, dict):
                x = position.get('x')
                y = position.get('y')
                if x is not None and y is not None:
                    return (float(x), float(y))
            elif isinstance(position, (list, tuple)) and len(position) >= 2:
                return (float(position[0]), float(position[1]))
        
        # 方法3: 从polygon计算中心点
        polygon = component.get('polygon')
        if polygon and len(polygon) >= 3:
            x_coords = [p[0] for p in polygon if len(p) >= 2]
            y_coords = [p[1] for p in polygon if len(p) >= 2]
            if x_coords and y_coords:
                center_x = sum(x_coords) / len(x_coords)
                center_y = sum(y_coords) / len(y_coords)
                return (center_x, center_y)
        
        return None
    
    def _point_in_slice(self, point: Tuple[float, float], 
                       slice_info: Dict[str, Any]) -> bool:
        """检查点是否在切片范围内"""
        x, y = point
        
        # 获取切片边界
        offset_x = slice_info.get('offset_x', 0)
        offset_y = slice_info.get('offset_y', 0)
        width = slice_info.get('slice_width', slice_info.get('width', 0))
        height = slice_info.get('slice_height', slice_info.get('height', 0))
        
        # 检查是否在范围内（包含容差）
        in_x_range = (offset_x - self.matching_tolerance <= x <= 
                      offset_x + width + self.matching_tolerance)
        in_y_range = (offset_y - self.matching_tolerance <= y <= 
                      offset_y + height + self.matching_tolerance)
        
        return in_x_range and in_y_range

# ============================================================================
# 改进2: 空间重叠 + 类型相似判定
# ============================================================================

class SpatialTypeMerger:
    """空间重叠和类型相似性合并器"""
    
    def __init__(self, iou_threshold: float = 0.5, similarity_threshold: float = 0.8):
        self.iou_threshold = iou_threshold
        self.similarity_threshold = similarity_threshold
        
        # 构件类型相似性映射
        self.type_similarity_groups = {
            '柱类': ['柱', '框架柱', '剪力墙柱', 'KZ', '异形柱'],
            '梁类': ['梁', '主梁', '次梁', 'GL', 'LL', '连梁'],
            '板类': ['板', '楼板', '屋面板', 'LB', '现浇板'],
            '墙类': ['墙', '剪力墙', '填充墙', 'QT', '挡土墙'],
            '基础类': ['基础', '独立基础', '条形基础', 'DJZ', 'TJZ']
        }
    
    def merge_components_by_spatial_and_type(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于空间重叠和类型相似性合并构件
        
        Args:
            components: 构件列表
            
        Returns:
            合并后的构件列表
        """
        if not components:
            return []
        
        logger.info(f"🔄 开始空间+类型合并: {len(components)} 个构件")
        
        merged_components = []
        used_indices = set()
        
        for i, component in enumerate(components):
            if i in used_indices:
                continue
            
            # 查找需要合并的构件
            merge_group = [i]
            
            for j, other_component in enumerate(components[i+1:], i+1):
                if j in used_indices:
                    continue
                
                # 检查合并条件
                should_merge = self._should_merge_components(component, other_component)
                
                if should_merge:
                    merge_group.append(j)
            
            # 执行合并
            if len(merge_group) > 1:
                merged_component = self._merge_component_group([components[idx] for idx in merge_group])
                merged_components.append(merged_component)
                used_indices.update(merge_group)
                logger.debug(f"📦 合并构件组: {len(merge_group)} 个构件 -> 1 个")
            else:
                merged_components.append(component)
                used_indices.add(i)
        
        logger.info(f"✅ 空间+类型合并完成: {len(components)} -> {len(merged_components)} 个构件")
        return merged_components
    
    def _should_merge_components(self, comp1: Dict[str, Any], comp2: Dict[str, Any]) -> bool:
        """判断两个构件是否应该合并"""
        # 条件1: 空间重叠检查
        spatial_overlap = self._calculate_spatial_overlap(comp1, comp2)
        
        # 条件2: 类型相似性检查
        type_similarity = self._calculate_type_similarity(comp1, comp2)
        
        # 条件3: 文本标签相似性检查（如果有）
        text_similarity = self._calculate_text_similarity(comp1, comp2)
        
        # 合并逻辑：满足任一强条件或多个弱条件组合
        strong_spatial = spatial_overlap > self.iou_threshold
        strong_type = type_similarity > self.similarity_threshold
        moderate_text = text_similarity > 0.6
        
        # 强条件：高空间重叠
        if strong_spatial:
            logger.debug(f"🎯 强空间重叠合并: IOU={spatial_overlap:.3f}")
            return True
        
        # 强条件：高类型相似性 + 中等空间重叠
        if strong_type and spatial_overlap > 0.2:
            logger.debug(f"🎯 类型+空间合并: 类型={type_similarity:.3f}, IOU={spatial_overlap:.3f}")
            return True
        
        # 弱条件组合：中等类型相似性 + 文本相似性 + 轻微空间重叠
        if type_similarity > 0.6 and moderate_text and spatial_overlap > 0.1:
            logger.debug(f"🎯 综合相似性合并: 类型={type_similarity:.3f}, 文本={text_similarity:.3f}, IOU={spatial_overlap:.3f}")
            return True
        
        return False
    
    def _calculate_spatial_overlap(self, comp1: Dict, comp2: Dict) -> float:
        """计算空间重叠度（IOU）"""
        bbox1 = comp1.get('bbox')
        bbox2 = comp2.get('bbox')
        
        if not bbox1 or not bbox2 or len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        return self._calculate_iou(bbox1, bbox2)
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个边界框的IOU"""
        # 计算交集
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # 计算并集
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_type_similarity(self, comp1: Dict, comp2: Dict) -> float:
        """计算类型相似性"""
        type1 = comp1.get('component_type', '').strip().lower()
        type2 = comp2.get('component_type', '').strip().lower()
        
        if not type1 or not type2:
            return 0.0
        
        # 完全匹配
        if type1 == type2:
            return 1.0
        
        # 检查是否在同一类型组
        for group_name, types in self.type_similarity_groups.items():
            types_lower = [t.lower() for t in types]
            if type1 in types_lower and type2 in types_lower:
                return 0.8
        
        # 子串匹配
        if type1 in type2 or type2 in type1:
            return 0.6
        
        return 0.0
    
    def _calculate_text_similarity(self, comp1: Dict, comp2: Dict) -> float:
        """计算文本标签相似性"""
        tags1 = set(comp1.get('text_tags', []))
        tags2 = set(comp2.get('text_tags', []))
        
        if not tags1 and not tags2:
            return 0.0
        
        if not tags1 or not tags2:
            return 0.0
        
        # Jaccard相似性
        intersection = len(tags1.intersection(tags2))
        union = len(tags1.union(tags2))
        
        return intersection / union if union > 0 else 0.0
    
    def _merge_component_group(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并一组构件"""
        if not components:
            return {}
        
        if len(components) == 1:
            return components[0]
        
        # 基础信息取第一个
        merged = components[0].copy()
        
        # 合并数量
        total_quantity = sum(comp.get('quantity', 0) for comp in components)
        merged['quantity'] = total_quantity
        
        # 合并边界框（外包矩形）
        all_bboxes = [comp.get('bbox') for comp in components if comp.get('bbox')]
        if all_bboxes:
            merged_bbox = [
                min(bbox[0] for bbox in all_bboxes),
                min(bbox[1] for bbox in all_bboxes),
                max(bbox[2] for bbox in all_bboxes),
                max(bbox[3] for bbox in all_bboxes)
            ]
            merged['bbox'] = merged_bbox
        
        # 合并文本标签
        all_tags = []
        for comp in components:
            tags = comp.get('text_tags', [])
            all_tags.extend(tags)
        
        # 去重保持顺序
        unique_tags = []
        seen = set()
        for tag in all_tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        merged['text_tags'] = unique_tags
        
        # 添加合并元数据
        merged['merge_metadata'] = {
            'merged_count': len(components),
            'merge_method': 'spatial_type_similarity',
            'original_ids': [comp.get('component_id', '') for comp in components],
            'confidence_scores': [comp.get('confidence', 0) for comp in components]
        }
        
        return merged

# ============================================================================
# 改进3: 切片内文本与构件联动
# ============================================================================

class TextComponentLinker:
    """文本与构件联动器"""
    
    def __init__(self, association_distance: float = 100):
        self.association_distance = association_distance  # 像素
        
        # 文本分类模式
        self.text_patterns = {
            'component_id': [
                r'^[A-Z]{1,2}\d{1,4}$',  # KZ1, GL201
                r'^[A-Z]{1,2}-\d{1,3}$'  # KZ-1
            ],
            'dimension': [
                r'^\d{2,4}[×xX]\d{2,4}$',           # 300×600
                r'^\d{2,4}[×xX]\d{2,4}[×xX]\d{2,4}$', # 300×600×800
                r'^[bBhH]?\d{2,4}$'                  # b300, h600
            ],
            'material': [
                r'^C\d{2}$',      # C30
                r'^HRB\d{3}$',    # HRB400
                r'^Q\d{3}$'       # Q235
            ],
            'reinforcement': [
                r'^\d+[φΦ]\d+',                    # 4φ12
                r'^[φΦ]\d+@\d+',                   # φ8@200
                r'^\d+[φΦ]\d+@\d+',                # 2φ12@150
            ]
        }
    
    def link_texts_to_components(self, components: List[Dict[str, Any]], 
                               text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将OCR文本关联到构件
        
        Args:
            components: 构件列表
            text_regions: 文本区域列表
            
        Returns:
            关联了文本的构件列表
        """
        logger.info(f"🔗 开始文本构件联动: {len(components)} 构件 × {len(text_regions)} 文本")
        
        linked_components = []
        
        for component in components:
            linked_component = component.copy()
            
            # 查找邻近文本
            nearby_texts = self._find_nearby_texts(component, text_regions)
            
            if nearby_texts:
                # 分类文本
                categorized_texts = self._categorize_texts(nearby_texts)
                
                # 添加到构件
                linked_component['text_tags'] = [t['text'] for t in nearby_texts]
                linked_component['categorized_texts'] = categorized_texts
                linked_component['text_association_count'] = len(nearby_texts)
                
                # 尝试从文本中增强构件信息
                enhanced_info = self._enhance_component_from_texts(categorized_texts)
                if enhanced_info:
                    linked_component['enhanced_from_text'] = enhanced_info
                
                logger.debug(f"🔗 构件 {component.get('component_id')} 关联了 {len(nearby_texts)} 个文本")
            else:
                linked_component['text_tags'] = []
                linked_component['categorized_texts'] = {}
                linked_component['text_association_count'] = 0
            
            linked_components.append(linked_component)
        
        associated_count = sum(1 for comp in linked_components if comp.get('text_tags'))
        logger.info(f"✅ 文本构件联动完成: {associated_count}/{len(components)} 个构件关联了文本")
        
        return linked_components
    
    def _find_nearby_texts(self, component: Dict[str, Any], 
                          text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找构件附近的文本"""
        component_bbox = component.get('bbox')
        if not component_bbox or len(component_bbox) < 4:
            return []
        
        component_center = (
            (component_bbox[0] + component_bbox[2]) / 2,
            (component_bbox[1] + component_bbox[3]) / 2
        )
        
        nearby_texts = []
        
        for text_region in text_regions:
            text_bbox = text_region.get('bbox', text_region.get('global_bbox'))
            if not text_bbox or len(text_bbox) < 4:
                continue
            
            text_center = (
                (text_bbox[0] + text_bbox[2]) / 2,
                (text_bbox[1] + text_bbox[3]) / 2
            )
            
            # 计算距离
            distance = math.sqrt(
                (component_center[0] - text_center[0])**2 + 
                (component_center[1] - text_center[1])**2
            )
            
            if distance <= self.association_distance:
                text_info = text_region.copy()
                text_info['distance_to_component'] = distance
                nearby_texts.append(text_info)
        
        # 按距离排序
        nearby_texts.sort(key=lambda x: x['distance_to_component'])
        
        return nearby_texts
    
    def _categorize_texts(self, text_regions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """对文本进行分类"""
        categorized = {category: [] for category in self.text_patterns.keys()}
        
        for text_region in text_regions:
            text = text_region.get('text', '').strip()
            if not text:
                continue
            
            # 检查文本属于哪个类别
            for category, patterns in self.text_patterns.items():
                for pattern in patterns:
                    import re
                    if re.match(pattern, text):
                        categorized[category].append(text)
                        break
        
        # 移除空类别
        return {k: v for k, v in categorized.items() if v}
    
    def _enhance_component_from_texts(self, categorized_texts: Dict[str, List[str]]) -> Dict[str, Any]:
        """从文本中增强构件信息"""
        enhanced = {}
        
        # 从尺寸文本中提取尺寸信息
        dimensions = categorized_texts.get('dimension', [])
        if dimensions:
            enhanced['extracted_dimensions'] = dimensions
            
            # 尝试解析具体尺寸值
            for dim_text in dimensions:
                parsed_dims = self._parse_dimension_text(dim_text)
                if parsed_dims:
                    enhanced['parsed_dimensions'] = parsed_dims
                    break
        
        # 从材料文本中提取材料信息
        materials = categorized_texts.get('material', [])
        if materials:
            enhanced['extracted_materials'] = materials
        
        # 从配筋文本中提取配筋信息
        reinforcements = categorized_texts.get('reinforcement', [])
        if reinforcements:
            enhanced['extracted_reinforcements'] = reinforcements
        
        return enhanced if enhanced else None
    
    def _parse_dimension_text(self, dim_text: str) -> Optional[Dict[str, float]]:
        """解析尺寸文本"""
        import re
        
        # 解析 300×600 格式
        match = re.match(r'^(\d{2,4})[×xX](\d{2,4})$', dim_text)
        if match:
            return {
                'width': float(match.group(1)),
                'height': float(match.group(2))
            }
        
        # 解析 300×600×800 格式
        match = re.match(r'^(\d{2,4})[×xX](\d{2,4})[×xX](\d{2,4})$', dim_text)
        if match:
            return {
                'width': float(match.group(1)),
                'height': float(match.group(2)),
                'depth': float(match.group(3))
            }
        
        # 解析 b300, h600 格式
        match = re.match(r'^[bB](\d{2,4})$', dim_text)
        if match:
            return {'width': float(match.group(1))}
        
        match = re.match(r'^[hH](\d{2,4})$', dim_text)
        if match:
            return {'height': float(match.group(1))}
        
        return None

# ============================================================================
# 改进4: 独立的OCR结果合并器
# ============================================================================

class IndependentOCRMerger:
    """独立的OCR结果合并器"""
    
    def __init__(self, iou_threshold: float = 0.7, distance_threshold: float = 50):
        self.iou_threshold = iou_threshold
        self.distance_threshold = distance_threshold
    
    def merge_all_ocr_results(self, slice_ocr_results: List[Dict[str, Any]], 
                            overlap_strategy: str = "IOU") -> List[Dict[str, Any]]:
        """
        合并所有切片的OCR结果
        
        Args:
            slice_ocr_results: 切片OCR结果列表
            overlap_strategy: 重叠处理策略 ("IOU", "distance", "hybrid")
            
        Returns:
            合并后的文本区域列表
        """
        logger.info(f"📝 开始OCR结果合并: {len(slice_ocr_results)} 个切片，策略={overlap_strategy}")
        
        # 步骤1: 收集所有文本区域并转换为全图坐标
        all_text_regions = []
        
        for slice_result in slice_ocr_results:
            if not slice_result.get('success', False):
                continue
            
            slice_id = slice_result.get('slice_id', '')
            offset_x = slice_result.get('offset_x', 0)
            offset_y = slice_result.get('offset_y', 0)
            text_regions = slice_result.get('text_regions', [])
            
            for region in text_regions:
                # 转换为全图坐标
                local_bbox = region.get('bbox', [0, 0, 0, 0])
                global_bbox = [
                    local_bbox[0] + offset_x,
                    local_bbox[1] + offset_y,
                    local_bbox[2] + offset_x,
                    local_bbox[3] + offset_y
                ]
                
                text_item = {
                    'text': region.get('text', ''),
                    'bbox': local_bbox,
                    'global_bbox': global_bbox,
                    'confidence': region.get('confidence', 0.0),
                    'slice_id': slice_id,
                    'original_slice_position': (offset_x, offset_y)
                }
                all_text_regions.append(text_item)
        
        logger.info(f"📊 收集到 {len(all_text_regions)} 个文本区域")
        
        # 步骤2: 根据策略合并重叠区域
        if overlap_strategy == "IOU":
            merged_regions = self._merge_by_iou(all_text_regions)
        elif overlap_strategy == "distance":
            merged_regions = self._merge_by_distance(all_text_regions)
        elif overlap_strategy == "hybrid":
            # 先IOU后距离
            iou_merged = self._merge_by_iou(all_text_regions)
            merged_regions = self._merge_by_distance(iou_merged)
        else:
            merged_regions = all_text_regions
        
        logger.info(f"✅ OCR合并完成: {len(all_text_regions)} -> {len(merged_regions)} 个区域")
        
        return merged_regions
    
    def _merge_by_iou(self, text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于IOU合并重叠文本"""
        merged = []
        used_indices = set()
        
        for i, region in enumerate(text_regions):
            if i in used_indices:
                continue
            
            # 查找重叠区域
            overlapping_indices = [i]
            
            for j, other_region in enumerate(text_regions[i+1:], i+1):
                if j in used_indices:
                    continue
                
                iou = self._calculate_bbox_iou(
                    region['global_bbox'], 
                    other_region['global_bbox']
                )
                
                if iou > self.iou_threshold:
                    overlapping_indices.append(j)
            
            # 合并重叠区域
            if len(overlapping_indices) > 1:
                merged_region = self._merge_text_regions([text_regions[idx] for idx in overlapping_indices])
                merged.append(merged_region)
                used_indices.update(overlapping_indices)
            else:
                merged.append(region)
                used_indices.add(i)
        
        return merged
    
    def _merge_by_distance(self, text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于距离合并邻近文本"""
        merged = []
        used_indices = set()
        
        for i, region in enumerate(text_regions):
            if i in used_indices:
                continue
            
            # 查找邻近区域
            nearby_indices = [i]
            region_center = self._get_bbox_center(region['global_bbox'])
            
            for j, other_region in enumerate(text_regions[i+1:], i+1):
                if j in used_indices:
                    continue
                
                other_center = self._get_bbox_center(other_region['global_bbox'])
                distance = math.sqrt(
                    (region_center[0] - other_center[0])**2 + 
                    (region_center[1] - other_center[1])**2
                )
                
                if distance < self.distance_threshold:
                    nearby_indices.append(j)
            
            # 合并邻近区域
            if len(nearby_indices) > 1:
                merged_region = self._merge_text_regions([text_regions[idx] for idx in nearby_indices])
                merged.append(merged_region)
                used_indices.update(nearby_indices)
            else:
                merged.append(region)
                used_indices.add(i)
        
        return merged
    
    def _calculate_bbox_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算边界框IOU"""
        if len(bbox1) != 4 or len(bbox2) != 4:
            return 0.0
        
        # 计算交集
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # 计算并集
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _get_bbox_center(self, bbox: List[float]) -> Tuple[float, float]:
        """获取边界框中心点"""
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def _merge_text_regions(self, regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个文本区域"""
        if not regions:
            return {}
        
        if len(regions) == 1:
            return regions[0]
        
        # 合并文本
        merged_text = " ".join([r['text'] for r in regions if r['text'].strip()])
        
        # 计算合并边界框
        all_global_bboxes = [r['global_bbox'] for r in regions]
        merged_global_bbox = [
            min(bbox[0] for bbox in all_global_bboxes),
            min(bbox[1] for bbox in all_global_bboxes),
            max(bbox[2] for bbox in all_global_bboxes),
            max(bbox[3] for bbox in all_global_bboxes)
        ]
        
        # 使用最高置信度
        merged_confidence = max(r['confidence'] for r in regions)
        
        # 合并切片信息
        slice_ids = list(set(r['slice_id'] for r in regions if r['slice_id']))
        
        return {
            'text': merged_text,
            'bbox': regions[0]['bbox'],  # 保留第一个的本地坐标
            'global_bbox': merged_global_bbox,
            'confidence': merged_confidence,
            'slice_id': ','.join(slice_ids),
            'merged_from': len(regions),
            'merge_method': 'ocr_overlap_merge'
        }

# ============================================================================
# 集成测试和验证
# ============================================================================

def test_enhanced_vision_components():
    """测试增强Vision组件"""
    print("🧪 测试增强Vision组件...")
    print("=" * 80)
    
    # 测试数据
    test_components = [
        {
            'component_id': 'KZ1',
            'component_type': '框架柱',
            'bbox': [100, 100, 200, 300],
            'quantity': 2,
            'confidence': 0.9
        },
        {
            'component_id': 'KZ2',
            'component_type': '柱',  # 相似类型
            'bbox': [150, 150, 250, 350],  # 有重叠
            'quantity': 1,
            'confidence': 0.85
        }
    ]
    
    test_slice_map = {
        'slice_0_0': {'offset_x': 0, 'offset_y': 0, 'slice_width': 500, 'slice_height': 500},
        'slice_0_1': {'offset_x': 400, 'offset_y': 0, 'slice_width': 500, 'slice_height': 500}
    }
    
    test_text_regions = [
        {'text': 'KZ1', 'bbox': [110, 80, 150, 100], 'confidence': 0.9},
        {'text': '300×600', 'bbox': [160, 80, 220, 100], 'confidence': 0.8},
        {'text': 'C30', 'bbox': [170, 320, 200, 340], 'confidence': 0.85}
    ]
    
    test_ocr_results = [
        {
            'slice_id': 'slice_0_0',
            'success': True,
            'offset_x': 0,
            'offset_y': 0,
            'text_regions': test_text_regions[:2]
        },
        {
            'slice_id': 'slice_0_1',
            'success': True,
            'offset_x': 400,
            'offset_y': 0,
            'text_regions': test_text_regions[2:]
        }
    ]
    
    # 测试1: 精确位置匹配
    print("1️⃣ 测试精确位置匹配...")
    matcher = PrecisePositionMatcher()
    for component in test_components:
        slice_id = matcher.match_component_to_slice(component, test_slice_map)
        print(f"   构件 {component['component_id']} -> 切片 {slice_id}")
    
    # 测试2: 空间类型合并
    print("\n2️⃣ 测试空间类型合并...")
    merger = SpatialTypeMerger(iou_threshold=0.3)
    merged_components = merger.merge_components_by_spatial_and_type(test_components)
    print(f"   合并前: {len(test_components)} 个构件")
    print(f"   合并后: {len(merged_components)} 个构件")
    for comp in merged_components:
        if 'merge_metadata' in comp:
            print(f"   合并构件: {comp['component_id']}, 原始数量: {comp['merge_metadata']['merged_count']}")
    
    # 测试3: 文本构件联动
    print("\n3️⃣ 测试文本构件联动...")
    linker = TextComponentLinker(association_distance=150)
    linked_components = linker.link_texts_to_components(test_components, test_text_regions)
    for comp in linked_components:
        if comp.get('text_tags'):
            print(f"   构件 {comp['component_id']} 关联文本: {comp['text_tags']}")
    
    # 测试4: OCR结果合并
    print("\n4️⃣ 测试OCR结果合并...")
    ocr_merger = IndependentOCRMerger()
    merged_ocr = ocr_merger.merge_all_ocr_results(test_ocr_results, overlap_strategy="hybrid")
    print(f"   OCR合并: {sum(len(r.get('text_regions', [])) for r in test_ocr_results)} -> {len(merged_ocr)} 个文本区域")
    for text in merged_ocr:
        print(f"   文本: '{text['text']}' 坐标: {text['global_bbox']}")
    
    print("\n✅ 所有测试完成！")

def generate_enhancement_summary():
    """生成改进方案总结"""
    summary = {
        'enhancement_title': 'VisionScannerService 四大核心改进',
        'improvements': [
            {
                'name': '精确位置匹配',
                'problem': '构件位置基于切片索引round-robin匹配不准确',
                'solution': '基于bbox中心点与slice_coordinate_map精确匹配',
                'benefits': ['提高构件来源准确性', '精确坐标还原', '减少匹配错误'],
                'implementation': 'PrecisePositionMatcher类'
            },
            {
                'name': '空间重叠+类型相似判定',
                'problem': '构件合并仅基于component_id，容易遗漏相似构件',
                'solution': 'IOU重叠检测 + 类型相似性 + 文本标签多维融合',
                'benefits': ['减少重复构件', '提高合并准确性', '支持异形构件处理'],
                'implementation': 'SpatialTypeMerger类'
            },
            {
                'name': '文本构件联动',
                'problem': 'OCR和Vision并行但缺乏深度整合',
                'solution': 'OCR文本按距离关联到构件，增强构件描述信息',
                'benefits': ['丰富构件信息', '自动提取规格参数', '提高识别完整性'],
                'implementation': 'TextComponentLinker类'
            },
            {
                'name': '独立OCR合并器',
                'problem': 'OCR合并逻辑分散，缺乏独立性和可测试性',
                'solution': '封装独立的OCR合并器，支持多种合并策略',
                'benefits': ['模块化设计', '可独立测试', '策略可配置'],
                'implementation': 'IndependentOCRMerger类'
            }
        ],
        'additional_enhancements': [
            {
                'name': 'Vision模型反馈标注热区',
                'description': '结合attention map可视化Vision检测置信区域',
                'implementation': '集成模型attention机制，生成热力图'
            },
            {
                'name': '构件分层图（楼层/图名）',
                'description': '结合图框识别模块，自动划分构件归属楼层',
                'implementation': '图框识别 + 构件空间分析'
            },
            {
                'name': '多轮GPT分析结构说明',
                'description': '对说明性文字单独调用GPT分析模型构造规则模板',
                'implementation': '专门的文本分析GPT调用链'
            },
            {
                'name': '单元测试/集成测试模块',
                'description': '针对每个_merge_xxx、_restore_xxx模块增加覆盖率',
                'implementation': '完整的测试套件，包含边界情况测试'
            }
        ],
        'performance_expectations': {
            'accuracy_improvement': '构件识别准确率提升15-25%',
            'merge_efficiency': '重复构件减少60%以上',
            'text_integration': '构件信息完整度提升40%',
            'maintainability': '代码模块化，测试覆盖率达到80%+'
        },
        'implementation_priority': [
            '1. 精确位置匹配（立即实施）',
            '2. OCR独立合并器（高优先级）',
            '3. 空间类型合并（中优先级）',
            '4. 文本构件联动（中优先级）',
            '5. 额外增强功能（低优先级）'
        ]
    }
    
    return summary

if __name__ == "__main__":
    # 运行测试
    test_enhanced_vision_components()
    
    # 输出改进方案总结
    print("\n" + "=" * 80)
    print("📋 VisionScannerService 改进方案总结")
    print("=" * 80)
    
    summary = generate_enhancement_summary()
    
    print(f"\n🎯 {summary['enhancement_title']}")
    print("-" * 50)
    
    for i, improvement in enumerate(summary['improvements'], 1):
        print(f"\n{i}. {improvement['name']}")
        print(f"   问题: {improvement['problem']}")
        print(f"   解决方案: {improvement['solution']}")
        print(f"   实现: {improvement['implementation']}")
        print(f"   收益: {', '.join(improvement['benefits'])}")
    
    print(f"\n📈 预期性能提升:")
    for key, value in summary['performance_expectations'].items():
        print(f"   • {key}: {value}")
    
    print(f"\n🏃 实施优先级:")
    for priority in summary['implementation_priority']:
        print(f"   {priority}")
    
    print("\n✅ 改进方案完成！建议立即开始实施前4项核心改进。") 