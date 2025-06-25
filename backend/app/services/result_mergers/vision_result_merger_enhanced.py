"""
增强版Vision分析结果合并器
实现精确位置匹配、空间重叠判定、OCR文本联动等高级功能
"""

import json
import time
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class TextRegion:
    """OCR文本区域"""
    text: str
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    slice_id: str
    global_bbox: Optional[List[float]] = None

@dataclass
class ComponentMatch:
    """构件匹配结果"""
    component: Dict[str, Any]
    source_slice_id: str
    confidence: float
    matched_texts: List[TextRegion]
    spatial_relation: Dict[str, Any]

class OCRResultMerger:
    """独立的OCR结果合并器"""
    
    def __init__(self, iou_threshold: float = 0.7):
        self.iou_threshold = iou_threshold
    
    def merge_all(self, slice_results: List[Dict], overlap_strategy: str = "IOU") -> List[TextRegion]:
        """
        合并所有切片的OCR结果
        
        Args:
            slice_results: 切片OCR结果列表
            overlap_strategy: 重叠处理策略 ("IOU", "distance", "hybrid")
            
        Returns:
            合并后的文本区域列表
        """
        logger.info(f"🔍 开始OCR结果合并: {len(slice_results)} 个切片，策略={overlap_strategy}")
        
        all_regions = []
        
        # 步骤1: 收集所有文本区域并转换为全图坐标
        for slice_result in slice_results:
            if not slice_result.get('success', False):
                continue
                
            slice_id = slice_result.get('slice_id', '')
            text_regions = slice_result.get('text_regions', [])
            
            for region in text_regions:
                text_region = TextRegion(
                    text=region.get('text', ''),
                    bbox=region.get('bbox', [0, 0, 0, 0]),
                    confidence=region.get('confidence', 0.0),
                    slice_id=slice_id,
                    global_bbox=self._convert_to_global_bbox(region.get('bbox', []), slice_result)
                )
                all_regions.append(text_region)
        
        logger.info(f"📊 收集到 {len(all_regions)} 个文本区域")
        
        # 步骤2: 根据策略合并重叠区域
        if overlap_strategy == "IOU":
            merged_regions = self._merge_by_iou(all_regions)
        elif overlap_strategy == "distance":
            merged_regions = self._merge_by_distance(all_regions)
        elif overlap_strategy == "hybrid":
            merged_regions = self._merge_by_hybrid(all_regions)
        else:
            merged_regions = all_regions
        
        logger.info(f"✅ OCR合并完成: {len(all_regions)} -> {len(merged_regions)} 个区域")
        return merged_regions
    
    def _convert_to_global_bbox(self, local_bbox: List[float], slice_result: Dict) -> List[float]:
        """将切片坐标转换为全图坐标"""
        if len(local_bbox) != 4:
            return [0, 0, 0, 0]
        
        offset_x = slice_result.get('offset_x', 0)
        offset_y = slice_result.get('offset_y', 0)
        
        return [
            local_bbox[0] + offset_x,
            local_bbox[1] + offset_y,
            local_bbox[2] + offset_x,
            local_bbox[3] + offset_y
        ]
    
    def _merge_by_iou(self, regions: List[TextRegion]) -> List[TextRegion]:
        """基于IOU合并重叠文本区域"""
        merged = []
        used_indices = set()
        
        for i, region in enumerate(regions):
            if i in used_indices:
                continue
            
            # 查找所有与当前区域重叠的区域
            overlapping_indices = [i]
            for j, other_region in enumerate(regions[i+1:], i+1):
                if j in used_indices:
                    continue
                
                iou = self._calculate_iou(region.global_bbox or region.bbox, 
                                        other_region.global_bbox or other_region.bbox)
                
                if iou > self.iou_threshold:
                    overlapping_indices.append(j)
            
            # 合并重叠区域
            if len(overlapping_indices) > 1:
                merged_region = self._merge_overlapping_regions([regions[idx] for idx in overlapping_indices])
                merged.append(merged_region)
                used_indices.update(overlapping_indices)
            else:
                merged.append(region)
                used_indices.add(i)
        
        return merged
    
    def _merge_by_distance(self, regions: List[TextRegion]) -> List[TextRegion]:
        """基于距离合并邻近文本区域"""
        # 距离阈值（像素）
        distance_threshold = 50
        
        merged = []
        used_indices = set()
        
        for i, region in enumerate(regions):
            if i in used_indices:
                continue
            
            # 查找邻近区域
            nearby_indices = [i]
            region_center = self._get_bbox_center(region.global_bbox or region.bbox)
            
            for j, other_region in enumerate(regions[i+1:], i+1):
                if j in used_indices:
                    continue
                
                other_center = self._get_bbox_center(other_region.global_bbox or other_region.bbox)
                distance = math.sqrt((region_center[0] - other_center[0])**2 + 
                                   (region_center[1] - other_center[1])**2)
                
                if distance < distance_threshold:
                    nearby_indices.append(j)
            
            # 合并邻近区域
            if len(nearby_indices) > 1:
                merged_region = self._merge_overlapping_regions([regions[idx] for idx in nearby_indices])
                merged.append(merged_region)
                used_indices.update(nearby_indices)
            else:
                merged.append(region)
                used_indices.add(i)
        
        return merged
    
    def _merge_by_hybrid(self, regions: List[TextRegion]) -> List[TextRegion]:
        """混合策略：先IOU再距离"""
        # 先基于IOU合并
        iou_merged = self._merge_by_iou(regions)
        
        # 再基于距离合并
        final_merged = self._merge_by_distance(iou_merged)
        
        return final_merged
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个边界框的IOU"""
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
        if len(bbox) != 4:
            return (0.0, 0.0)
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def _merge_overlapping_regions(self, regions: List[TextRegion]) -> TextRegion:
        """合并多个重叠的文本区域"""
        if not regions:
            return None
        
        if len(regions) == 1:
            return regions[0]
        
        # 合并文本内容
        merged_text = " ".join([r.text for r in regions if r.text.strip()])
        
        # 计算合并后的边界框
        all_bboxes = [r.global_bbox or r.bbox for r in regions if (r.global_bbox or r.bbox)]
        if all_bboxes:
            merged_bbox = [
                min(bbox[0] for bbox in all_bboxes),  # min x1
                min(bbox[1] for bbox in all_bboxes),  # min y1
                max(bbox[2] for bbox in all_bboxes),  # max x2
                max(bbox[3] for bbox in all_bboxes)   # max y2
            ]
        else:
            merged_bbox = [0, 0, 0, 0]
        
        # 使用最高置信度
        merged_confidence = max(r.confidence for r in regions)
        
        # 合并切片ID
        slice_ids = list(set(r.slice_id for r in regions if r.slice_id))
        merged_slice_id = ",".join(slice_ids)
        
        return TextRegion(
            text=merged_text,
            bbox=merged_bbox,
            confidence=merged_confidence,
            slice_id=merged_slice_id,
            global_bbox=merged_bbox
        )

class EnhancedVisionResultMerger:
    """增强版Vision分析结果合并器"""
    
    def __init__(self):
        self.ocr_merger = OCRResultMerger(iou_threshold=0.7)
        self.spatial_iou_threshold = 0.5
        self.text_association_distance = 100  # 像素
    
    def merge_vision_results_enhanced(self, 
                                    vision_results: List[Dict[str, Any]], 
                                    slice_coordinate_map: Dict[str, Any],
                                    original_image_info: Dict[str, Any],
                                    ocr_results: List[Dict] = None,
                                    task_id: str = "") -> Dict[str, Any]:
        """
        增强版Vision结果合并
        
        Args:
            vision_results: Vision分析结果列表
            slice_coordinate_map: 切片坐标映射
            original_image_info: 原图信息
            ocr_results: OCR结果（可选）
            task_id: 任务ID
            
        Returns:
            增强合并结果
        """
        logger.info(f"🚀 开始增强版Vision结果合并: {len(vision_results)} 个结果")
        start_time = time.time()
        
        # 步骤1: 精确位置匹配 - 基于bbox中心而非索引匹配
        matched_components = self._match_components_by_position(vision_results, slice_coordinate_map)
        logger.info(f"📍 位置匹配完成: {len(matched_components)} 个构件")
        
        # 步骤2: 合并OCR结果（如果提供）
        merged_texts = []
        if ocr_results:
            merged_texts = self.ocr_merger.merge_all(ocr_results, overlap_strategy="hybrid")
            logger.info(f"📝 OCR合并完成: {len(merged_texts)} 个文本区域")
        
        # 步骤3: 文本与构件联动 - 将OCR文本关联到构件
        components_with_texts = self._associate_texts_with_components(matched_components, merged_texts)
        logger.info(f"🔗 文本构件联动完成: {len(components_with_texts)} 个构件")
        
        # 步骤4: 空间重叠+类型相似判定合并
        final_components = self._merge_by_spatial_and_type_similarity(components_with_texts)
        logger.info(f"🔄 空间类型合并完成: {len(final_components)} 个构件")
        
        # 步骤5: 生成增强结果
        enhanced_result = self._generate_enhanced_result(
            final_components, original_image_info, task_id, 
            start_time, len(vision_results), merged_texts
        )
        
        processing_time = time.time() - start_time
        logger.info(f"✅ 增强版Vision合并完成: 耗时 {processing_time:.2f}s")
        
        return enhanced_result
    
    def _match_components_by_position(self, vision_results: List[Dict], 
                                    slice_coordinate_map: Dict[str, Any]) -> List[ComponentMatch]:
        """基于bbox中心精确匹配构件位置"""
        logger.info("🎯 开始精确位置匹配...")
        
        matched_components = []
        
        for result in vision_results:
            if not result.get('success', False):
                continue
            
            qto_data = result.get('qto_data', {})
            components = qto_data.get('components', [])
            
            for component in components:
                # 获取构件的边界框
                bbox = component.get('bbox')
                position = component.get('position')
                
                if not bbox and not position:
                    logger.warning(f"⚠️ 构件缺少位置信息: {component.get('component_id', 'unknown')}")
                    continue
                
                # 计算构件中心点
                if bbox and len(bbox) >= 4:
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2
                elif position:
                    if isinstance(position, dict):
                        center_x = position.get('x', 0)
                        center_y = position.get('y', 0)
                    elif isinstance(position, list) and len(position) >= 2:
                        center_x = position[0]
                        center_y = position[1]
                    else:
                        continue
                else:
                    continue
                
                # 查找匹配的切片
                matched_slice_id = self._find_slice_by_center(center_x, center_y, slice_coordinate_map)
                
                if matched_slice_id:
                    # 转换为全图坐标
                    global_component = self._convert_component_to_global_coordinates(
                        component, matched_slice_id, slice_coordinate_map
                    )
                    
                    match = ComponentMatch(
                        component=global_component,
                        source_slice_id=matched_slice_id,
                        confidence=component.get('confidence', 0.8),
                        matched_texts=[],
                        spatial_relation={}
                    )
                    matched_components.append(match)
                else:
                    logger.warning(f"⚠️ 无法匹配切片: 构件中心点({center_x}, {center_y})")
        
        return matched_components
    
    def _find_slice_by_center(self, center_x: float, center_y: float, 
                            slice_coordinate_map: Dict[str, Any]) -> Optional[str]:
        """根据中心点查找对应的切片"""
        for slice_id, slice_info in slice_coordinate_map.items():
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            width = slice_info.get('slice_width', slice_info.get('width', 0))
            height = slice_info.get('slice_height', slice_info.get('height', 0))
            
            # 检查中心点是否在切片范围内
            if (offset_x <= center_x <= offset_x + width and 
                offset_y <= center_y <= offset_y + height):
                return slice_id
        
        return None
    
    def _convert_component_to_global_coordinates(self, component: Dict, 
                                               slice_id: str, 
                                               slice_coordinate_map: Dict) -> Dict:
        """将构件坐标转换为全图坐标"""
        slice_info = slice_coordinate_map.get(slice_id, {})
        offset_x = slice_info.get('offset_x', 0)
        offset_y = slice_info.get('offset_y', 0)
        
        global_component = component.copy()
        
        # 转换边界框
        if 'bbox' in component and len(component['bbox']) >= 4:
            bbox = component['bbox']
            global_component['bbox'] = [
                bbox[0] + offset_x,
                bbox[1] + offset_y,
                bbox[2] + offset_x,
                bbox[3] + offset_y
            ]
        
        # 转换位置
        if 'position' in component:
            position = component['position']
            if isinstance(position, dict):
                global_component['position'] = {
                    'x': position.get('x', 0) + offset_x,
                    'y': position.get('y', 0) + offset_y
                }
            elif isinstance(position, list) and len(position) >= 2:
                global_component['position'] = [
                    position[0] + offset_x,
                    position[1] + offset_y
                ]
        
        # 添加切片来源信息
        global_component['slice_source'] = {
            'slice_id': slice_id,
            'offset': (offset_x, offset_y)
        }
        
        return global_component
    
    def _associate_texts_with_components(self, component_matches: List[ComponentMatch], 
                                       text_regions: List[TextRegion]) -> List[ComponentMatch]:
        """将OCR文本与构件关联"""
        logger.info(f"🔗 开始文本构件联动: {len(component_matches)} 构件 × {len(text_regions)} 文本")
        
        for match in component_matches:
            component = match.component
            component_bbox = component.get('bbox')
            
            if not component_bbox or len(component_bbox) < 4:
                continue
            
            # 查找邻近的文本
            nearby_texts = []
            for text_region in text_regions:
                text_bbox = text_region.global_bbox or text_region.bbox
                
                if not text_bbox or len(text_bbox) < 4:
                    continue
                
                # 计算距离
                distance = self._calculate_bbox_distance(component_bbox, text_bbox)
                
                if distance <= self.text_association_distance:
                    nearby_texts.append(text_region)
            
            # 将文本添加到构件
            match.matched_texts = nearby_texts
            
            # 更新构件的文本标签
            if nearby_texts:
                text_tags = [t.text for t in nearby_texts if t.text.strip()]
                component['text_tags'] = text_tags
                component['associated_text_count'] = len(nearby_texts)
                
                # 尝试从文本中提取规格信息
                extracted_specs = self._extract_specs_from_texts(text_tags)
                if extracted_specs:
                    component['extracted_specifications'] = extracted_specs
        
        return component_matches
    
    def _calculate_bbox_distance(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算两个边界框的最短距离"""
        # 获取中心点
        center1 = ((bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2)
        center2 = ((bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2)
        
        # 计算中心点距离
        return math.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
    
    def _extract_specs_from_texts(self, texts: List[str]) -> Dict[str, Any]:
        """从文本中提取规格信息"""
        specs = {}
        
        for text in texts:
            # 尺寸信息
            dimension_patterns = [
                r'(\d+)\s*[xX×]\s*(\d+)',  # 300x600
                r'[bBhH]?\s*(\d+)',        # b300, h600
                r'(\d+)\s*mm'              # 300mm
            ]
            
            for pattern in dimension_patterns:
                import re
                matches = re.findall(pattern, text)
                if matches:
                    specs['dimensions'] = matches
                    break
            
            # 材料信息
            material_patterns = [
                r'C\d{2}',      # C30
                r'HRB\d{3}',    # HRB400
                r'Q\d{3}'       # Q235
            ]
            
            for pattern in material_patterns:
                import re
                matches = re.findall(pattern, text)
                if matches:
                    specs['materials'] = matches
                    break
        
        return specs
    
    def _merge_by_spatial_and_type_similarity(self, component_matches: List[ComponentMatch]) -> List[Dict]:
        """基于空间重叠和类型相似性合并构件"""
        logger.info(f"🔄 开始空间类型合并: {len(component_matches)} 个构件")
        
        merged_components = []
        used_indices = set()
        
        for i, match in enumerate(component_matches):
            if i in used_indices:
                continue
            
            component = match.component
            
            # 查找需要合并的构件
            merge_candidates = [i]
            
            for j, other_match in enumerate(component_matches[i+1:], i+1):
                if j in used_indices:
                    continue
                
                other_component = other_match.component
                
                # 检查空间重叠
                spatial_overlap = self._check_spatial_overlap(component, other_component)
                
                # 检查类型相似性
                type_similarity = self._check_type_similarity(component, other_component)
                
                # 如果满足合并条件
                if spatial_overlap > self.spatial_iou_threshold or type_similarity > 0.8:
                    merge_candidates.append(j)
            
            # 执行合并
            if len(merge_candidates) > 1:
                merged_component = self._merge_similar_components([component_matches[idx] for idx in merge_candidates])
                merged_components.append(merged_component)
                used_indices.update(merge_candidates)
                logger.debug(f"📦 合并构件: {len(merge_candidates)} 个 -> 1 个")
            else:
                merged_components.append(component)
                used_indices.add(i)
        
        logger.info(f"✅ 空间类型合并完成: {len(component_matches)} -> {len(merged_components)} 个构件")
        return merged_components
    
    def _check_spatial_overlap(self, comp1: Dict, comp2: Dict) -> float:
        """检查两个构件的空间重叠度"""
        bbox1 = comp1.get('bbox')
        bbox2 = comp2.get('bbox')
        
        if not bbox1 or not bbox2 or len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        return self.ocr_merger._calculate_iou(bbox1, bbox2)
    
    def _check_type_similarity(self, comp1: Dict, comp2: Dict) -> float:
        """检查两个构件的类型相似性"""
        type1 = comp1.get('component_type', '').lower()
        type2 = comp2.get('component_type', '').lower()
        
        if not type1 or not type2:
            return 0.0
        
        # 简单的字符串相似度
        if type1 == type2:
            return 1.0
        
        # 检查是否是相似类型（如：梁 vs 主梁）
        similar_types = [
            ['梁', '主梁', '次梁'],
            ['柱', '框架柱', '剪力墙柱'],
            ['板', '楼板', '屋面板'],
            ['墙', '剪力墙', '填充墙']
        ]
        
        for group in similar_types:
            if type1 in group and type2 in group:
                return 0.8
        
        return 0.0
    
    def _merge_similar_components(self, matches: List[ComponentMatch]) -> Dict:
        """合并相似的构件"""
        if not matches:
            return {}
        
        if len(matches) == 1:
            return matches[0].component
        
        # 基础信息使用第一个构件
        merged = matches[0].component.copy()
        
        # 合并数量
        total_quantity = sum(match.component.get('quantity', 0) for match in matches)
        merged['quantity'] = total_quantity
        
        # 合并文本标签
        all_text_tags = []
        for match in matches:
            text_tags = match.component.get('text_tags', [])
            all_text_tags.extend(text_tags)
        
        if all_text_tags:
            # 去重并保持顺序
            unique_tags = []
            seen = set()
            for tag in all_text_tags:
                if tag not in seen:
                    unique_tags.append(tag)
                    seen.add(tag)
            merged['text_tags'] = unique_tags
        
        # 合并边界框（取外包矩形）
        all_bboxes = [match.component.get('bbox') for match in matches if match.component.get('bbox')]
        if all_bboxes:
            merged_bbox = [
                min(bbox[0] for bbox in all_bboxes),  # min x1
                min(bbox[1] for bbox in all_bboxes),  # min y1
                max(bbox[2] for bbox in all_bboxes),  # max x2
                max(bbox[3] for bbox in all_bboxes)   # max y2
            ]
            merged['bbox'] = merged_bbox
        
        # 合并切片来源
        slice_sources = [match.source_slice_id for match in matches]
        merged['slice_sources'] = list(set(slice_sources))
        
        # 添加合并元数据
        merged['merge_metadata'] = {
            'merged_count': len(matches),
            'merge_method': 'spatial_and_type_similarity',
            'confidence_scores': [match.confidence for match in matches]
        }
        
        return merged
    
    def _generate_enhanced_result(self, final_components: List[Dict], 
                                original_image_info: Dict, task_id: str,
                                start_time: float, input_count: int,
                                merged_texts: List[TextRegion]) -> Dict[str, Any]:
        """生成增强合并结果"""
        processing_time = time.time() - start_time
        
        # 构件类型分布统计
        type_distribution = {}
        for comp in final_components:
            comp_type = comp.get('component_type', '未知')
            type_distribution[comp_type] = type_distribution.get(comp_type, 0) + 1
        
        # 文本统计
        text_stats = {
            'total_text_regions': len(merged_texts),
            'associated_texts': sum(1 for comp in final_components if comp.get('text_tags')),
            'average_texts_per_component': len([comp for comp in final_components if comp.get('text_tags')]) / len(final_components) if final_components else 0
        }
        
        return {
            'success': True,
            'task_id': task_id,
            'enhanced_result': {
                'components': final_components,
                'component_count': len(final_components),
                'type_distribution': type_distribution,
                'text_integration': text_stats,
                'processing_metadata': {
                    'input_vision_results': input_count,
                    'final_components': len(final_components),
                    'processing_time_seconds': processing_time,
                    'enhancement_features': [
                        'precise_position_matching',
                        'spatial_overlap_detection',
                        'text_component_association',
                        'type_similarity_merging'
                    ]
                }
            },
            'original_image_info': original_image_info,
            'timestamp': time.time()
        } 