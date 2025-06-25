#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision结果协调器组件
负责结果合并、坐标恢复和存储管理
"""
import logging
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VisionResultCoordinator:
    """Vision结果协调器"""
    
    def __init__(self):
        """初始化结果协调器"""
        self.logger = logger
        
    async def merge_and_store_results(self, 
                                    batch_results: Dict[str, Any], 
                                    drawing_id: int,
                                    batch_id: str = None) -> Dict[str, Any]:
        """
        合并批次结果并存储
        
        Args:
            batch_results: 批次处理结果
            drawing_id: 图纸ID
            batch_id: 批次ID
            
        Returns:
            最终合并和存储结果
        """
        logger.info(f"🔗 开始结果协调 - 图纸ID: {drawing_id}")
        
        try:
            if not batch_results.get("success", False):
                logger.error("❌ 批次结果不成功，无法进行协调")
                return batch_results
            
            # 获取构件列表
            components = batch_results.get("components", [])
            if not components:
                logger.warning("⚠️ 没有构件数据需要协调")
                return {
                    "success": True,
                    "components": [],
                    "merged_component_count": 0,
                    "coordinate_restored": False,
                    "storage_saved": False
                }
            
            logger.info(f"📊 开始协调 {len(components)} 个构件")
            
            # 第一步：坐标恢复和合并
            restored_components = self._restore_coordinates_and_merge_components(
                components, batch_results.get("batch_summary", {})
            )
            
            # 第二步：保存结果到存储
            storage_result = await self._save_merged_vision_result(
                restored_components, drawing_id, batch_id
            )
            
            # 构建最终结果
            final_result = {
                "success": True,
                "components": restored_components,
                "merged_component_count": len(restored_components),
                "coordinate_restored": True,
                "storage_saved": storage_result.get("success", False),
                "batch_summary": batch_results.get("batch_summary", {}),
                "storage_details": storage_result
            }
            
            if storage_result.get("warnings"):
                final_result["warnings"] = storage_result["warnings"]
            
            logger.info(f"✅ 结果协调完成: {len(restored_components)} 个最终构件")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 结果协调异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "components": [],
                "merged_component_count": 0,
                "coordinate_restored": False,
                "storage_saved": False
            }

    def _restore_coordinates_and_merge_components(self, 
                                                components: List[Dict[str, Any]], 
                                                batch_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        恢复全局坐标并合并重复构件
        
        Args:
            components: 构件列表
            batch_summary: 批次摘要信息
            
        Returns:
            处理后的构件列表
        """
        logger.info(f"🔄 开始坐标恢复和构件合并...")
        
        try:
            # 第一步：坐标恢复（如果需要）
            restored_components = []
            for component in components:
                restored_component = self._restore_component_coordinates(component)
                restored_components.append(restored_component)
            
            # 第二步：合并重复构件
            merged_components = self._merge_duplicate_components(restored_components)
            
            # 第三步：验证和标准化
            validated_components = self._validate_and_standardize_components(merged_components)
            
            logger.info(f"✅ 坐标恢复和合并完成: {len(components)} → {len(validated_components)} 个构件")
            return validated_components
            
        except Exception as e:
            logger.error(f"❌ 坐标恢复和合并异常: {e}", exc_info=True)
            return components  # 返回原始构件列表

    def _restore_component_coordinates(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """恢复单个构件的全局坐标"""
        restored_component = component.copy()
        
        # 如果构件包含切片相关的坐标信息，进行恢复
        batch_index = component.get("batch_index")
        if batch_index is not None:
            # 添加全局坐标恢复逻辑
            # 这里可以根据切片的边界信息恢复全局坐标
            restored_component["coordinate_restored"] = True
            restored_component["global_coordinates"] = self._calculate_global_coordinates(component)
        
        return restored_component

    def _calculate_global_coordinates(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """计算构件的全局坐标"""
        # 简化的全局坐标计算
        # 实际实现需要根据切片信息和图纸比例进行精确计算
        batch_index = component.get("batch_index", 0)
        
        # 假设的坐标偏移计算
        offset_x = batch_index * 1000  # 简化的X偏移
        offset_y = 0  # 简化的Y偏移
        
        return {
            "x_offset": offset_x,
            "y_offset": offset_y,
            "calculation_method": "simplified_batch_offset"
        }

    def _merge_duplicate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并重复构件 - 增强版
        使用基于空间重叠和ID相似性的策略
        """
        if not components:
            return []

        # 1. 对构件进行预处理和标准化
        processed_components = []
        for i, comp in enumerate(components):
            comp['temp_id'] = i  # 添加临时唯一ID
            comp['merged'] = False
            # 确保bbox存在且有效
            if 'bbox' not in comp or not isinstance(comp.get('bbox'), list) or len(comp.get('bbox')) != 4:
                comp['bbox'] = [0, 0, 0, 0] # 提供一个默认bbox避免后续错误
            processed_components.append(comp)

        # 2. 迭代合并，直到没有构件可以合并为止
        merged_run = True
        while merged_run:
            merged_run = False
            merged_indices = set()
            new_components_list = []
            
            # 使用索引来遍历，方便在循环中修改列表
            for i in range(len(processed_components)):
                if processed_components[i]['merged']:
                    continue

                group_to_merge = [processed_components[i]]
                
                for j in range(i + 1, len(processed_components)):
                    if processed_components[j]['merged']:
                        continue
                    
                    # 检查是否应该合并
                    if self._should_merge(processed_components[i], processed_components[j]):
                        group_to_merge.append(processed_components[j])
                        processed_components[j]['merged'] = True
                        merged_run = True # 标记发生了合并

                if len(group_to_merge) > 1:
                    merged_component = self._merge_component_group(group_to_merge)
                    merged_component['merged'] = False # 重置合并状态
                    new_components_list.append(merged_component)
                else:
                    new_components_list.append(processed_components[i])

            processed_components = new_components_list

        final_components = [comp for comp in processed_components if not comp.get('merged')]
        
        logger.info(f"🔄 构件合并完成: {len(components)} → {len(final_components)} 个构件")
        return final_components

    def _should_merge(self, comp1: Dict[str, Any], comp2: Dict[str, Any], iou_threshold: float = 0.5) -> bool:
        """判断两个构件是否应该合并"""
        
        # 规则1: 基于ID的精确匹配 (如果ID可靠)
        id1 = comp1.get("component_id")
        id2 = comp2.get("component_id")
        if id1 and id2 and id1 == id2:
             # 如果ID相同，计算IoU来确认是否为同一实例
            iou = self._calculate_iou(comp1.get('bbox', []), comp2.get('bbox', []))
            if iou > iou_threshold:
                return True

        # 规则2: 基于类型和空间重叠
        type1 = comp1.get("component_type")
        type2 = comp2.get("component_type")
        if type1 and type2 and type1 == type2:
            iou = self._calculate_iou(comp1.get('bbox', []), comp2.get('bbox', []))
            if iou > iou_threshold:
                return True
        
        return False

    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """计算两个边界框的交并比 (IoU)"""
        if not box1 or not box2:
            return 0.0

        x1_inter = max(box1[0], box2[0])
        y1_inter = max(box1[1], box2[1])
        x2_inter = min(box1[2], box2[2])
        y2_inter = min(box1[3], box2[3])

        inter_area = max(0, x2_inter - x1_inter) * max(0, y2_inter - y1_inter)
        if inter_area == 0:
            return 0.0

        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = box1_area + box2_area - inter_area
        if union_area == 0:
            return 0.0
            
        return inter_area / union_area

    def _merge_component_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并一组相同ID的构件 - 增强版
        智能合并属性
        """
        if not group:
            return {}
        
        # 以信息最丰富的构件为基础
        base_component = max(group, key=lambda c: len(json.dumps(c.get('dimensions', {}))) + len(json.dumps(c.get('primitives', []))))
        merged = base_component.copy()
        
        # 合并数量
        total_quantity = sum(self._safe_get_number(comp, "quantity", 1) for comp in group)
        
        # 合并几何信息 (bbox)
        all_x = []
        all_y = []
        for comp in group:
            bbox = comp.get('bbox')
            if bbox:
                all_x.extend([bbox[0], bbox[2]])
                all_y.extend([bbox[1], bbox[3]])
        
        if all_x and all_y:
            merged['bbox'] = [min(all_x), min(all_y), max(all_x), max(all_y)]
            
        # 合并其他属性
        merged["quantity"] = total_quantity
        merged["merged_from_count"] = len(group)
        merged["merge_sources"] = [comp.get("batch_index", -1) for comp in group]
        
        # 清理临时字段
        merged.pop('temp_id', None)
        merged.pop('merged', None)

        return merged

    def _validate_and_standardize_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证和标准化构件数据"""
        validated_components = []
        
        for component in components:
            try:
                validated_component = self._validate_single_component(component)
                if validated_component:
                    validated_components.append(validated_component)
                else:
                    logger.warning(f"⚠️ 构件验证失败，已跳过: {component.get('component_id', 'unknown')}")
            except Exception as e:
                logger.warning(f"⚠️ 构件验证异常，已跳过: {e}")
        
        return validated_components

    def _validate_single_component(self, component: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """验证单个构件"""
        # 检查必要字段
        component_id = component.get("component_id")
        if not component_id:
            return None
        
        # 标准化构件类型
        component_type = component.get("component_type", "未知构件")
        standardized_type = self._standardize_component_type(component_type)
        
        # 创建验证后的构件
        validated = component.copy()
        validated["component_type"] = standardized_type
        validated["validation_passed"] = True
        validated["validation_timestamp"] = time.time()
        
        return validated

    def _standardize_component_type(self, component_type: str) -> str:
        """标准化构件类型"""
        type_mapping = {
            "柱": "框架柱",
            "梁": "框架梁", 
            "板": "现浇板",
            "墙": "剪力墙",
            "基础": "独立基础"
        }
        
        for key, standard_type in type_mapping.items():
            if key in component_type:
                return standard_type
        
        return component_type

    async def _save_merged_vision_result(self, 
                                       components: List[Dict[str, Any]], 
                                       drawing_id: int,
                                       batch_id: str = None) -> Dict[str, Any]:
        """保存合并后的Vision结果"""
        logger.info(f"💾 开始保存Vision结果 - 图纸ID: {drawing_id}, 构件数量: {len(components)}")
        
        try:
            # 构建结果数据
            result_data = {
                "drawing_id": drawing_id,
                "batch_id": batch_id,
                "components": components,
                "component_count": len(components),
                "analysis_type": "vision_scan",
                "timestamp": time.time(),
                "result_id": str(uuid.uuid4())
            }
            
            # 导入存储服务
            try:
                from app.services.sealos_storage import SealosStorage
                storage_service = SealosStorage()
                
                # 保存到Sealos存储
                result_uuid = result_data["result_id"]
                s3_key = f"vision_results/{drawing_id}/vision_merged_{result_uuid}.json"
                
                save_result = storage_service.save_json_data(s3_key, result_data)
                
                if save_result.get("success", False):
                    logger.info(f"✅ Vision结果已保存到Sealos: {s3_key}")
                    return {
                        "success": True,
                        "storage_location": s3_key,
                        "result_id": result_uuid,
                        "component_count": len(components)
                    }
                else:
                    logger.error(f"❌ Sealos保存失败: {save_result.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": save_result.get("error", "Sealos保存失败"),
                        "fallback_saved": False
                    }
                    
            except ImportError:
                logger.warning("⚠️ Sealos存储服务不可用，跳过保存")
                return {
                    "success": False,
                    "error": "存储服务不可用",
                    "fallback_saved": False
                }
                
        except Exception as e:
            logger.error(f"❌ 保存Vision结果异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "fallback_saved": False
            }

    def _safe_get_number(self, data: Dict[str, Any], key: str, default: float = 0.0) -> float:
        """安全获取数字值"""
        value = data.get(key, default)
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return default
        
        return default 