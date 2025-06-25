#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果融合器
从enhanced_grid_slice_analyzer.py中提取的双轨结果融合功能
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict

from ..enhanced_slice_models import EnhancedSliceInfo
from app.utils.analysis_optimizations import CoordinateTransformService

logger = logging.getLogger(__name__)

class ResultMerger:
    """结果融合器 - 负责融合OCR和Vision分析结果"""
    
    def __init__(self, coordinate_service: Optional[CoordinateTransformService] = None):
        self.coordinate_service = coordinate_service
        self.merged_components = []
    
    def merge_dual_track_results(self, ocr_results: List[Dict[str, Any]], 
                               vision_results: List[Dict[str, Any]],
                               enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        """融合双轨分析结果"""
        try:
            # 初始化融合统计
            merge_stats = {
                "ocr_components": len(ocr_results),
                "vision_components": sum(len(vr.get("components", [])) for vr in vision_results),
                "merged_components": 0,
                "fusion_conflicts": 0,
                "coordinate_restored": 0
            }
            
            # 提取Vision构件
            all_vision_components = []
            for vision_result in vision_results:
                if vision_result.get("success") and vision_result.get("components"):
                    all_vision_components.extend(vision_result["components"])
            
            # 按切片分组进行融合
            slice_groups = self._group_components_by_slice(all_vision_components, enhanced_slices)
            
            # 执行融合
            merged_components = []
            for slice_id, slice_components in slice_groups.items():
                slice_info = self._find_slice_info(slice_id, enhanced_slices)
                if slice_info:
                    merged_slice_components = self._merge_slice_components(
                        slice_components, slice_info
                    )
                    merged_components.extend(merged_slice_components)
            
            # 坐标恢复
            if self.coordinate_service:
                restored_components = self._restore_global_coordinates(merged_components)
                merge_stats["coordinate_restored"] = len(restored_components)
            else:
                restored_components = merged_components
                logger.warning("⚠️ 坐标转换服务未初始化，跳过坐标恢复")
            
            # 去重和优化
            final_components = self._deduplicate_components(restored_components)
            
            merge_stats["merged_components"] = len(final_components)
            self.merged_components = final_components
            
            logger.info(f"✅ 双轨结果融合完成: {merge_stats}")
            
            return {
                "success": True,
                "merged_components": final_components,
                "merge_statistics": merge_stats,
                "total_components": len(final_components)
            }
            
        except Exception as e:
            logger.error(f"❌ 双轨结果融合失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _group_components_by_slice(self, vision_components: List[Dict[str, Any]], 
                                  enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, List[Dict[str, Any]]]:
        """按切片对构件进行分组"""
        slice_groups = defaultdict(list)
        
        for component in vision_components:
            slice_id = component.get("slice_id", "")
            if slice_id:
                slice_groups[slice_id].append(component)
            else:
                # 如果没有slice_id，尝试根据其他信息推断
                inferred_slice_id = self._infer_slice_id(component, enhanced_slices)
                if inferred_slice_id:
                    slice_groups[inferred_slice_id].append(component)
        
        return dict(slice_groups)
    
    def _infer_slice_id(self, component: Dict[str, Any], 
                       enhanced_slices: List[EnhancedSliceInfo]) -> Optional[str]:
        """推断构件所属的切片ID"""
        component_id = component.get("component_id", "")
        if component_id:
            # 查找包含相似构件编号的切片
            for slice_info in enhanced_slices:
                if hasattr(slice_info, 'ocr_classification') and slice_info.ocr_classification:
                    slice_component_ids = slice_info.ocr_classification.get("component_ids", [])
                    if any(component_id in ocr_id for ocr_id in slice_component_ids):
                        return slice_info.slice_id
        
        return None
    
    def _find_slice_info(self, slice_id: str, 
                        enhanced_slices: List[EnhancedSliceInfo]) -> Optional[EnhancedSliceInfo]:
        """查找切片信息"""
        for slice_info in enhanced_slices:
            if slice_info.slice_id == slice_id:
                return slice_info
        return None
    
    def _merge_slice_components(self, vision_components: List[Dict[str, Any]], 
                              slice_info: EnhancedSliceInfo) -> List[Dict[str, Any]]:
        """融合单个切片的构件信息"""
        try:
            merged_components = []
            
            # 获取切片的OCR信息
            ocr_classification = getattr(slice_info, 'ocr_classification', {})
            ocr_component_ids = ocr_classification.get("component_ids", [])
            ocr_dimensions = ocr_classification.get("dimensions", [])
            ocr_specs = ocr_classification.get("technical_specs", [])
            
            for vision_component in vision_components:
                merged_component = self._merge_single_component(
                    vision_component, ocr_component_ids, ocr_dimensions, ocr_specs
                )
                if merged_component:
                    merged_components.append(merged_component)
            
            return merged_components
            
        except Exception as e:
            logger.warning(f"⚠️ 融合切片构件失败 {slice_info.slice_id}: {e}")
            return vision_components  # 返回原始Vision结果
    
    def _merge_single_component(self, vision_component: Dict[str, Any],
                               ocr_component_ids: List[str],
                               ocr_dimensions: List[str],
                               ocr_specs: List[str]) -> Optional[Dict[str, Any]]:
        """融合单个构件的信息"""
        try:
            merged = vision_component.copy()
            
            # 增强构件编号匹配
            vision_id = vision_component.get("component_id", "")
            if vision_id:
                matched_ocr_id = self._find_matching_ocr_id(vision_id, ocr_component_ids)
                if matched_ocr_id:
                    merged["ocr_matched_id"] = matched_ocr_id
                    merged["confidence"] = merged.get("confidence", 0.5) + 0.3
            
            # 增强尺寸信息
            vision_dims = vision_component.get("dimensions")
            if not vision_dims or not isinstance(vision_dims, dict) or not vision_dims:
                matched_dimension = self._find_matching_dimension(vision_id, ocr_dimensions)
                if matched_dimension:
                    merged["dimensions"] = self._parse_ocr_dimension(matched_dimension)
                    merged["dimension_source"] = "ocr_enhanced"
            
            # 设置融合标记
            merged["fusion_method"] = "vision_ocr_enhanced"
            merged["data_sources"] = ["vision", "ocr"]
            
            return merged
            
        except Exception as e:
            logger.warning(f"⚠️ 融合单个构件失败: {e}")
            return vision_component
    
    def _find_matching_ocr_id(self, vision_id: str, ocr_ids: List[str]) -> Optional[str]:
        """在OCR结果中查找匹配的构件编号"""
        if not vision_id:
            return None
        
        # 精确匹配
        for ocr_id in ocr_ids:
            if vision_id.upper() == ocr_id.upper():
                return ocr_id
        
        # 模糊匹配
        for ocr_id in ocr_ids:
            if vision_id.upper() in ocr_id.upper() or ocr_id.upper() in vision_id.upper():
                return ocr_id
        
        return None
    
    def _find_matching_dimension(self, component_id: str, dimensions: List[str]) -> Optional[str]:
        """查找匹配的尺寸信息"""
        return dimensions[0] if dimensions else None
    
    def _parse_ocr_dimension(self, dimension_str: str) -> Dict[str, Any]:
        """解析OCR识别的尺寸字符串"""
        try:
            if 'x' in dimension_str.lower() or '×' in dimension_str:
                parts = dimension_str.replace('×', 'x').split('x')
                if len(parts) >= 2:
                    return {
                        "width": parts[0].strip(),
                        "height": parts[1].strip(),
                        "source": "ocr_parsed"
                    }
            return {"raw": dimension_str, "source": "ocr_raw"}
        except Exception:
            return {"raw": dimension_str, "source": "ocr_raw"}
    
    def _restore_global_coordinates(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """恢复全局坐标"""
        if not self.coordinate_service:
            return components
        
        restored_components = []
        for component in components:
            restored_component = component.copy()
            
            # 获取切片内坐标
            local_position = component.get("position")
            slice_id = component.get("slice_id")
            
            if local_position and slice_id:
                try:
                    # 转换为全局坐标
                    global_position = self.coordinate_service.transform_to_global(
                        local_position, slice_id
                    )
                    if global_position:
                        restored_component["global_position"] = global_position
                        restored_component["coordinate_restored"] = True
                except Exception as e:
                    logger.warning(f"⚠️ 坐标转换失败 {slice_id}: {e}")
                    restored_component["coordinate_restored"] = False
            
            restored_components.append(restored_component)
        
        return restored_components
    
    def _deduplicate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复构件"""
        seen_ids = set()
        deduplicated = []
        
        for component in components:
            component_id = component.get("component_id", "")
            
            if component_id and component_id not in seen_ids:
                seen_ids.add(component_id)
                deduplicated.append(component)
            elif not component_id:
                # 没有ID的构件保留
                deduplicated.append(component)
        
        return deduplicated 