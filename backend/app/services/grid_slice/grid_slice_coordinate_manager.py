#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片坐标管理器
负责坐标转换和切片坐标管理
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GridSliceCoordinateManager:
    """网格切片坐标管理器"""
    
    def __init__(self, core_analyzer):
        """初始化坐标管理器"""
        self.core_analyzer = core_analyzer
        self.coordinate_service = None

    def initialize_coordinate_service(self, slice_coordinate_map: Dict[str, Any], original_image_info: Dict[str, Any]):
        """初始化坐标转换服务"""
        try:
            from app.utils.analysis_optimizations import CoordinateTransformService
            self.coordinate_service = CoordinateTransformService(slice_coordinate_map, original_image_info)
            self.core_analyzer.coordinate_service = self.coordinate_service
            logger.info("✅ 坐标转换服务初始化成功")
        except Exception as e:
            logger.error(f"❌ 坐标转换服务初始化失败: {e}")

    def restore_global_coordinates(self, image_path: str) -> Dict[str, Any]:
        """还原全局坐标系统"""
        try:
            logger.info("🗺️ 开始还原全局坐标系统")
            
            if not self.coordinate_service:
                logger.warning("⚠️ 坐标转换服务未初始化，跳过坐标还原")
                return {"success": False, "error": "坐标转换服务未初始化"}
            
            restored_components = []
            
            # 遍历所有合并后的构件
            for component in self.core_analyzer.merged_components:
                try:
                    # 获取切片坐标信息
                    source_slice = component.get("source_slice", "")
                    slice_coordinates = component.get("slice_coordinates", {})
                    
                    if not source_slice or not slice_coordinates:
                        logger.warning(f"⚠️ 构件 {component.get('component_id', 'unknown')} 缺少坐标信息")
                        restored_components.append(component)
                        continue
                    
                    # 还原到全局坐标
                    global_coordinates = self._restore_component_coordinates(component, slice_coordinates)
                    
                    # 更新构件坐标信息
                    restored_component = component.copy()
                    restored_component["global_coordinates"] = global_coordinates
                    restored_component["coordinate_restored"] = True
                    
                    restored_components.append(restored_component)
                    
                except Exception as comp_error:
                    logger.warning(f"⚠️ 构件坐标还原失败: {comp_error}")
                    restored_components.append(component)
                    continue
            
            # 更新核心分析器中的构件列表
            self.core_analyzer.merged_components = restored_components
            
            logger.info(f"✅ 坐标还原完成，处理 {len(restored_components)} 个构件")
            
            return {
                "success": True,
                "restored_count": len(restored_components),
                "components": restored_components
            }
            
        except Exception as e:
            logger.error(f"❌ 全局坐标还原失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _restore_component_coordinates(self, component: Dict[str, Any], slice_coordinates: Dict[str, Any]) -> Dict[str, Any]:
        """还原单个构件的坐标"""
        try:
            # 从切片坐标转换为全局坐标
            slice_x_offset = slice_coordinates.get("x_offset", 0)
            slice_y_offset = slice_coordinates.get("y_offset", 0)
            slice_width = slice_coordinates.get("width", 0)
            slice_height = slice_coordinates.get("height", 0)
            
            # 假设构件在切片中的相对位置（这里需要根据实际Vision分析结果来确定）
            # 目前使用切片中心作为构件位置
            relative_x = slice_width // 2
            relative_y = slice_height // 2
            
            # 转换为全局坐标
            global_x = slice_x_offset + relative_x
            global_y = slice_y_offset + relative_y
            
            global_coordinates = {
                "global_x": global_x,
                "global_y": global_y,
                "slice_x_offset": slice_x_offset,
                "slice_y_offset": slice_y_offset,
                "relative_x": relative_x,
                "relative_y": relative_y,
                "coordinate_method": "slice_center_estimation"
            }
            
            return global_coordinates
            
        except Exception as e:
            logger.error(f"❌ 单个构件坐标还原失败: {e}")
            return {}

    def build_slice_coordinate_map(self) -> Dict[str, Any]:
        """构建切片坐标映射"""
        try:
            coordinate_map = {}
            
            for slice_info in self.core_analyzer.enhanced_slices:
                slice_key = f"{slice_info.row}_{slice_info.col}"
                coordinate_map[slice_key] = {
                    "x_offset": slice_info.x_offset,
                    "y_offset": slice_info.y_offset,
                    "width": slice_info.width,
                    "height": slice_info.height,
                    "row": slice_info.row,
                    "col": slice_info.col,
                    "source_page": slice_info.source_page
                }
            
            logger.info(f"📍 构建切片坐标映射完成，包含 {len(coordinate_map)} 个切片")
            return coordinate_map
            
        except Exception as e:
            logger.error(f"❌ 构建切片坐标映射失败: {e}")
            return {}

    def validate_coordinate_consistency(self) -> Dict[str, Any]:
        """验证坐标一致性"""
        try:
            inconsistent_components = []
            total_components = len(self.core_analyzer.merged_components)
            
            for component in self.core_analyzer.merged_components:
                # 检查坐标信息完整性
                issues = []
                
                if not component.get("source_slice"):
                    issues.append("缺少source_slice信息")
                
                if not component.get("slice_coordinates"):
                    issues.append("缺少slice_coordinates信息")
                
                if not component.get("global_coordinates"):
                    issues.append("缺少global_coordinates信息")
                
                if issues:
                    inconsistent_components.append({
                        "component_id": component.get("component_id", "unknown"),
                        "issues": issues
                    })
            
            logger.info(f"📊 坐标一致性验证完成: {total_components} 个构件中有 {len(inconsistent_components)} 个存在问题")
            
            return {
                "success": True,
                "total_components": total_components,
                "inconsistent_count": len(inconsistent_components),
                "inconsistent_components": inconsistent_components,
                "consistency_rate": (total_components - len(inconsistent_components)) / total_components if total_components > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ 坐标一致性验证失败: {e}")
            return {"success": False, "error": str(e)}

    def get_coordinate_statistics(self) -> Dict[str, Any]:
        """获取坐标统计信息"""
        try:
            stats = {
                "total_slices": len(self.core_analyzer.enhanced_slices),
                "total_components": len(self.core_analyzer.merged_components),
                "coordinate_service_available": self.coordinate_service is not None,
                "slices_with_coordinates": 0,
                "components_with_global_coordinates": 0
            }
            
            # 统计具有坐标的切片数量
            for slice_info in self.core_analyzer.enhanced_slices:
                if hasattr(slice_info, 'x_offset') and hasattr(slice_info, 'y_offset'):
                    stats["slices_with_coordinates"] += 1
            
            # 统计具有全局坐标的构件数量
            for component in self.core_analyzer.merged_components:
                if component.get("global_coordinates"):
                    stats["components_with_global_coordinates"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取坐标统计信息失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        if self.coordinate_service:
            self.coordinate_service = None
        logger.info("🧹 坐标管理器已清理") 