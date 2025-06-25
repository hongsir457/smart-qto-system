#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片结果合并器
负责双轨分析结果的合并和工程量清单生成
"""

import logging
import re
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class GridSliceResultMerger:
    """网格切片结果合并器"""
    
    def __init__(self, core_analyzer):
        """初始化结果合并器"""
        self.core_analyzer = core_analyzer

    def merge_dual_track_results(self) -> Dict[str, Any]:
        """合并双轨分析结果"""
        try:
            logger.info("🔄 开始合并双轨分析结果")
            
            # 收集所有切片的构件
            all_components = []
            
            for slice_key, slice_components in self.core_analyzer.slice_components.items():
                for component in slice_components:
                    # 添加切片标识
                    component["source_slice"] = slice_key
                    all_components.append(component)
            
            logger.info(f"📊 收集到 {len(all_components)} 个原始构件")
            
            # 去重和合并相似构件
            merged_components = self._merge_similar_components(all_components)
            
            # 验证和清理构件数据
            cleaned_components = self._validate_and_clean_components(merged_components)
            
            # 更新核心分析器
            self.core_analyzer.merged_components = cleaned_components
            
            logger.info(f"✅ 结果合并完成: {len(cleaned_components)} 个有效构件")
            
            return {
                "success": True,
                "original_count": len(all_components),
                "merged_count": len(merged_components),
                "final_count": len(cleaned_components),
                "components": cleaned_components
            }
            
        except Exception as e:
            logger.error(f"❌ 双轨结果合并失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _merge_similar_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并相似的构件"""
        try:
            # 按构件ID分组
            component_groups = defaultdict(list)
            
            for component in components:
                component_id = component.get("component_id", "").strip()
                if component_id:
                    component_groups[component_id].append(component)
                else:
                    # 没有ID的构件单独处理
                    component_groups[f"no_id_{id(component)}"].append(component)
            
            merged_components = []
            
            for component_id, component_list in component_groups.items():
                if len(component_list) == 1:
                    # 单个构件直接添加
                    merged_components.append(component_list[0])
                else:
                    # 多个构件需要合并
                    merged_component = self._merge_component_group(component_list)
                    merged_components.append(merged_component)
            
            logger.info(f"📊 构件合并: {len(components)} → {len(merged_components)}")
            return merged_components
            
        except Exception as e:
            logger.error(f"❌ 合并相似构件失败: {e}")
            return components

    def _merge_component_group(self, component_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并同一组的构件"""
        try:
            # 选择置信度最高的构件作为基础
            base_component = max(component_list, key=lambda c: c.get("confidence", 0))
            
            # 合并其他信息
            merged_component = base_component.copy()
            
            # 收集所有源切片
            source_slices = []
            for comp in component_list:
                if comp.get("source_slice"):
                    source_slices.append(comp["source_slice"])
            
            merged_component["source_slices"] = list(set(source_slices))
            merged_component["merge_count"] = len(component_list)
            merged_component["merge_method"] = "confidence_based"
            
            # 合并尺寸信息（取最详细的）
            dimensions_list = [comp.get("dimensions", "") for comp in component_list if comp.get("dimensions")]
            if dimensions_list:
                # 选择最长的尺寸描述
                merged_component["dimensions"] = max(dimensions_list, key=len)
            
            # 合并材料信息
            materials_list = [comp.get("material", "") for comp in component_list if comp.get("material")]
            if materials_list:
                merged_component["material"] = max(materials_list, key=len)
            
            return merged_component
            
        except Exception as e:
            logger.error(f"❌ 合并构件组失败: {e}")
            return component_list[0] if component_list else {}

    def _validate_and_clean_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证和清理构件数据"""
        try:
            cleaned_components = []
            
            for component in components:
                # 基本验证
                if not component.get("component_id") and not component.get("component_type"):
                    logger.warning("⚠️ 跳过无效构件：缺少ID和类型")
                    continue
                
                # 清理和标准化数据
                cleaned_component = self._clean_component_data(component)
                
                if cleaned_component:
                    cleaned_components.append(cleaned_component)
            
            logger.info(f"📊 构件清理: {len(components)} → {len(cleaned_components)}")
            return cleaned_components
            
        except Exception as e:
            logger.error(f"❌ 验证清理构件失败: {e}")
            return components

    def _clean_component_data(self, component: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """清理单个构件数据"""
        try:
            cleaned = {}
            
            # 清理构件ID
            component_id = component.get("component_id", "").strip()
            if component_id:
                cleaned["component_id"] = self._standardize_component_id(component_id)
            
            # 清理构件类型
            component_type = component.get("component_type", "").strip()
            if component_type:
                cleaned["component_type"] = self._standardize_component_type(component_type)
            
            # 清理尺寸信息
            dimensions = component.get("dimensions", "").strip()
            if dimensions:
                cleaned["dimensions"] = self._standardize_dimensions(dimensions)
                # 解析尺寸并计算工程量
                parsed_dimensions = self._parse_dimensions(dimensions)
                if parsed_dimensions:
                    cleaned.update(parsed_dimensions)
            
            # 清理材料信息
            material = component.get("material", "").strip()
            if material:
                cleaned["material"] = self._standardize_material(material)
            
            # 保留其他重要信息
            for key in ["confidence", "source_slice", "source_slices", "slice_coordinates", 
                       "analysis_method", "position", "merge_count", "merge_method"]:
                if key in component:
                    cleaned[key] = component[key]
            
            return cleaned if cleaned else None
            
        except Exception as e:
            logger.error(f"❌ 清理构件数据失败: {e}")
            return component

    def _standardize_component_id(self, component_id: str) -> str:
        """标准化构件ID"""
        # 移除多余空格和特殊字符
        cleaned_id = re.sub(r'\s+', '', component_id.upper())
        return cleaned_id

    def _standardize_component_type(self, component_type: str) -> str:
        """标准化构件类型"""
        type_mapping = {
            "梁": "梁",
            "BEAM": "梁",
            "柱": "柱", 
            "COLUMN": "柱",
            "板": "板",
            "SLAB": "板",
            "墙": "墙",
            "WALL": "墙",
            "基础": "基础",
            "FOUNDATION": "基础"
        }
        
        cleaned_type = component_type.strip().upper()
        return type_mapping.get(cleaned_type, component_type)

    def _standardize_dimensions(self, dimensions: str) -> str:
        """标准化尺寸信息"""
        # 统一乘号
        dimensions = re.sub(r'[xX×*]', '×', dimensions)
        # 移除多余空格
        dimensions = re.sub(r'\s+', '', dimensions)
        return dimensions

    def _standardize_material(self, material: str) -> str:
        """标准化材料信息"""
        return material.strip().upper()

    def _parse_dimensions(self, dimensions: str) -> Optional[Dict[str, Any]]:
        """解析尺寸信息"""
        try:
            # 提取数字
            numbers = re.findall(r'\d+', dimensions)
            if not numbers:
                return None
            
            # 转换为整数
            values = [int(n) for n in numbers]
            
            result = {}
            if len(values) >= 2:
                result["length"] = values[0]
                result["width"] = values[1]
                if len(values) >= 3:
                    result["height"] = values[2]
                
                # 计算基本工程量
                if len(values) == 2:
                    result["area"] = values[0] * values[1] / 1000000  # 转换为平方米
                elif len(values) >= 3:
                    result["volume"] = values[0] * values[1] * values[2] / 1000000000  # 转换为立方米
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 解析尺寸失败: {e}")
            return None

    def generate_quantity_list_display(self) -> Dict[str, Any]:
        """生成工程量清单显示"""
        try:
            logger.info("📋 生成工程量清单显示")
            
            # 按构件类型分组统计
            component_stats = defaultdict(list)
            total_area = 0
            total_volume = 0
            
            for component in self.core_analyzer.merged_components:
                comp_type = component.get("component_type", "未知类型")
                component_stats[comp_type].append(component)
                
                # 累计工程量
                if "area" in component:
                    total_area += component["area"]
                if "volume" in component:
                    total_volume += component["volume"]
            
            # 生成清单项
            quantity_items = []
            for comp_type, components in component_stats.items():
                type_area = sum(comp.get("area", 0) for comp in components)
                type_volume = sum(comp.get("volume", 0) for comp in components)
                
                quantity_items.append({
                    "component_type": comp_type,
                    "count": len(components),
                    "total_area": round(type_area, 2),
                    "total_volume": round(type_volume, 3),
                    "components": components
                })
            
            # 排序（按数量降序）
            quantity_items.sort(key=lambda x: x["count"], reverse=True)
            
            return {
                "quantity_list": quantity_items,
                "summary": {
                    "total_components": len(self.core_analyzer.merged_components),
                    "component_types": len(component_stats),
                    "total_area": round(total_area, 2),
                    "total_volume": round(total_volume, 3),
                    "analysis_method": "dual_track_enhanced"
                },
                "generation_time": "实时生成",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ 生成工程量清单失败: {e}")
            return {
                "quantity_list": [],
                "summary": {
                    "total_components": 0,
                    "component_types": 0,
                    "total_area": 0,
                    "total_volume": 0,
                    "analysis_method": "dual_track_enhanced"
                },
                "status": "error",
                "error": str(e)
            }

    def get_merge_statistics(self) -> Dict[str, Any]:
        """获取合并统计信息"""
        try:
            stats = {
                "total_merged_components": len(self.core_analyzer.merged_components),
                "components_with_merge_info": 0,
                "average_confidence": 0,
                "component_type_distribution": defaultdict(int)
            }
            
            confidences = []
            for component in self.core_analyzer.merged_components:
                if "merge_count" in component:
                    stats["components_with_merge_info"] += 1
                
                confidence = component.get("confidence", 0)
                if confidence > 0:
                    confidences.append(confidence)
                
                comp_type = component.get("component_type", "未知")
                stats["component_type_distribution"][comp_type] += 1
            
            if confidences:
                stats["average_confidence"] = round(sum(confidences) / len(confidences), 3)
            
            return dict(stats)
            
        except Exception as e:
            logger.error(f"❌ 获取合并统计失败: {e}")
            return {}

    def cleanup(self):
        """清理资源"""
        # 清理临时合并数据
        pass 