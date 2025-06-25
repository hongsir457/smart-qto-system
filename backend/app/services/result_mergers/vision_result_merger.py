"""
Vision分析结果合并器
用于合并多个切片的Vision分析结果，生成统一的结构化清单
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VisionFullResult:
    """Vision全图分析合并结果"""
    task_id: str
    original_image_info: Dict[str, Any]
    total_slices: int
    successful_slices: int
    
    # 项目信息（最完整的一份）
    project_info: Dict[str, Any]
    
    # 合并后的构件信息
    merged_components: List[Dict[str, Any]]
    component_summary: Dict[str, Any]
    
    # 整合的图纸说明和施工要求
    integrated_descriptions: Dict[str, Any]
    
    # 统计信息
    total_components: int
    component_types_distribution: Dict[str, int]
    
    # 处理信息
    merge_metadata: Dict[str, Any]
    timestamp: float

class VisionResultMerger:
    """Vision分析结果合并器"""
    
    def __init__(self, storage_service=None):
        self.storage_service = storage_service
    
    def merge_vision_results(self, 
                           vision_results: List[Dict[str, Any]], 
                           slice_coordinate_map: Dict[str, Any],
                           original_image_info: Dict[str, Any],
                           task_id: str) -> VisionFullResult:
        """
        合并所有切片的Vision分析结果
        
        Args:
            vision_results: 切片Vision分析结果列表
            slice_coordinate_map: 切片坐标映射表
            original_image_info: 原图信息
            task_id: 任务ID
            
        Returns:
            合并后的Vision全图分析结果
        """
        logger.info(f"🔄 开始合并Vision分析结果: {len(vision_results)} 个切片")
        start_time = time.time()
        
        # 1. 提取并选择最完整的项目信息
        project_info = self._merge_project_info(vision_results)
        
        # 2. 还原构件坐标并合并
        merged_components = self._merge_and_restore_components(
            vision_results, slice_coordinate_map
        )
        
        # 3. 整合图纸说明和施工要求
        integrated_descriptions = self._integrate_descriptions(vision_results)
        
        # 4. 生成构件汇总统计
        component_summary = self._generate_component_summary(merged_components)
        
        # 5. 统计构件类型分布
        component_types_distribution = self._calculate_component_distribution(merged_components)
        
        # 6. 生成合并元数据
        merge_metadata = self._generate_merge_metadata(
            vision_results, len(merged_components), start_time
        )
        
        # 7. 创建合并结果
        vision_full_result = VisionFullResult(
            task_id=task_id,
            original_image_info=original_image_info,
            total_slices=len(vision_results),
            successful_slices=len([r for r in vision_results if r.get('success', False)]),
            
            project_info=project_info,
            merged_components=merged_components,
            component_summary=component_summary,
            integrated_descriptions=integrated_descriptions,
            
            total_components=len(merged_components),
            component_types_distribution=component_types_distribution,
            
            merge_metadata=merge_metadata,
            timestamp=time.time()
        )
        
        logger.info(f"✅ Vision分析结果合并完成: {len(merged_components)} 个构件")
        return vision_full_result
    
    def _merge_project_info(self, vision_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并项目信息，保留最完整的一份"""
        
        all_project_info = []
        
        for result in vision_results:
            if not result.get('success', False):
                continue
                
            qto_data = result.get('qto_data', {})
            
            # 获取项目信息
            project_info = {}
            
            # 从drawing_info中提取
            drawing_info = qto_data.get('drawing_info', {})
            if drawing_info:
                project_info.update({
                    'drawing_title': drawing_info.get('title'),
                    'drawing_scale': drawing_info.get('scale'),
                    'drawing_number': drawing_info.get('drawing_number'),
                    'floor_info': drawing_info.get('floor_info')
                })
            
            # 从project_analysis中提取
            project_analysis = qto_data.get('project_analysis', {})
            if project_analysis:
                project_info.update({
                    'project_name': project_analysis.get('project_name'),
                    'company_name': project_analysis.get('company_name'),
                    'design_phase': project_analysis.get('design_phase')
                })
            
            # 从其他可能的字段中提取
            for key in ['project_name', 'company_name', 'drawing_name', 'scale', 'drawing_number']:
                if key in qto_data and qto_data[key]:
                    project_info[key] = qto_data[key]
            
            if project_info:
                all_project_info.append(project_info)
        
        if not all_project_info:
            return {}
        
        # 选择最完整的项目信息（字段最多且非空值最多）
        best_project_info = max(all_project_info, key=lambda x: (
            len([v for v in x.values() if v and v != 'Unknown' and v != 'N/A']),
            len(x)
        ))
        
        logger.info(f"✅ 选择最完整的项目信息: {len(best_project_info)} 个字段")
        return best_project_info
    
    def _merge_and_restore_components(self, 
                                    vision_results: List[Dict[str, Any]], 
                                    slice_coordinate_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """合并并还原构件坐标"""
        
        all_components = []
        
        logger.info(f"🔍 开始处理 {len(vision_results)} 个Vision结果进行构件合并...")
        logger.info(f"📍 切片坐标映射: {len(slice_coordinate_map)} 个切片")
        
        for i, result in enumerate(vision_results):
            logger.info(f"🔎 处理结果 {i}: success={result.get('success', False)}")
            
            if not result.get('success', False):
                logger.debug(f"跳过失败的结果 {i}")
                continue
            
            qto_data = result.get('qto_data', {})
            components = qto_data.get('components', [])
            
            logger.info(f"📋 切片 {i} 包含 {len(components)} 个构件")
            
            # 详细记录构件信息
            if components:
                for j, comp in enumerate(components[:3]):  # 只显示前3个构件的详细信息
                    comp_type = comp.get('component_type', comp.get('type', 'unknown'))
                    comp_id = comp.get('component_id', comp.get('id', 'no-id'))
                    logger.debug(f"  构件 {j}: {comp_type} (ID: {comp_id})")
            
            if not components:
                logger.debug(f"切片 {i} 没有构件，跳过")
                continue
            
            # 获取该切片的坐标信息
            slice_info = slice_coordinate_map.get(i, {})
            if not slice_info:
                # 使用默认坐标信息
                slice_info = {
                    'offset_x': 0,
                    'offset_y': 0,
                    'slice_id': f'slice_{i}',
                    'slice_width': 1024,
                    'slice_height': 1024
                }
                logger.warning(f"⚠️  切片 {i} 没有坐标映射信息，使用默认值")
            
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            
            logger.debug(f"切片 {i} 坐标偏移: ({offset_x}, {offset_y})")
            
            # 还原每个构件的坐标
            restored_count = 0
            for j, component in enumerate(components):
                logger.debug(f"处理构件 {j}: {component.get('component_type', 'unknown')}")
                
                restored_component = self._restore_component_coordinates(
                    component, offset_x, offset_y, slice_info, i
                )
                if restored_component:
                    all_components.append(restored_component)
                    restored_count += 1
                    logger.debug(f"✓ 构件 {j} 坐标还原成功")
                else:
                    logger.warning(f"⚠️  构件 {j} 坐标还原失败")
            
            logger.info(f"✅ 切片 {i}: {restored_count}/{len(components)} 个构件还原成功")
        
        logger.info(f"📊 收集到 {len(all_components)} 个原始构件进行聚合")
        
        # 按构件ID和属性聚合去重
        if all_components:
            merged_components = self._aggregate_duplicate_components(all_components)
            logger.info(f"✅ 构件坐标还原和聚合完成: {len(all_components)} -> {len(merged_components)} 个构件")
        else:
            merged_components = []
            logger.warning("⚠️  没有构件可以合并")
        
        return merged_components
    
    def _restore_component_coordinates(self, 
                                     component: Dict[str, Any], 
                                     offset_x: int, 
                                     offset_y: int,
                                     slice_info: Dict[str, Any],
                                     slice_index: int) -> Optional[Dict[str, Any]]:
        """还原构件坐标到原图坐标系"""
        
        if not component:
            return None
        
        restored_component = component.copy()
        
        # 还原位置信息
        if 'position' in component:
            position = component['position']
            if isinstance(position, dict) and 'x' in position and 'y' in position:
                restored_component['position'] = {
                    'x': position['x'] + offset_x,
                    'y': position['y'] + offset_y
                }
            elif isinstance(position, list) and len(position) >= 2:
                restored_component['position'] = [
                    position[0] + offset_x,
                    position[1] + offset_y
                ]
        
        # 还原边界框
        if 'bbox' in component:
            bbox = component['bbox']
            if isinstance(bbox, list) and len(bbox) >= 4:
                restored_component['bbox'] = [
                    bbox[0] + offset_x,  # x1
                    bbox[1] + offset_y,  # y1
                    bbox[2] + offset_x,  # x2
                    bbox[3] + offset_y   # y2
                ]
        
        # 还原中心点
        if 'center' in component:
            center = component['center']
            if isinstance(center, list) and len(center) >= 2:
                restored_component['center'] = [
                    center[0] + offset_x,
                    center[1] + offset_y
                ]
        
        # 还原多边形坐标
        if 'polygon' in component:
            polygon = component['polygon']
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
                restored_component['polygon'] = restored_polygon
        
        # 添加切片来源信息
        restored_component['slice_source'] = {
            'slice_index': slice_index,
            'slice_id': slice_info.get('slice_id', f'slice_{slice_index}'),
            'offset': (offset_x, offset_y),
            'slice_bounds': (
                slice_info.get('offset_x', 0),
                slice_info.get('offset_y', 0),
                slice_info.get('slice_width', 0),
                slice_info.get('slice_height', 0)
            )
        }
        
        return restored_component
    
    def _aggregate_duplicate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按构件ID或坐标聚合重复构件"""
        
        if not components:
            return []
        
        logger.info(f"🔄 开始构件聚合: {len(components)} 个构件")
        
        # 构件聚合字典
        aggregated = {}
        
        for component in components:
            # 生成聚合键
            agg_key = self._generate_component_aggregation_key(component)
            
            if agg_key in aggregated:
                # 合并重复构件
                existing = aggregated[agg_key]
                
                # 合并数量
                existing_qty = existing.get('quantity', 1)
                new_qty = component.get('quantity', 1)
                existing['quantity'] = existing_qty + new_qty
                
                # 合并切片来源
                existing_sources = existing.get('slice_sources', [])
                new_source = component.get('slice_source', {})
                if new_source and new_source not in existing_sources:
                    existing_sources.append(new_source)
                existing['slice_sources'] = existing_sources
                
                # 融合属性（选择更完整的）
                self._merge_component_attributes(existing, component)
                
                logger.debug(f"📦 聚合构件: {agg_key}, 数量: {existing_qty} + {new_qty} = {existing['quantity']}")
                
            else:
                # 新构件
                component['slice_sources'] = [component.get('slice_source', {})]
                if 'slice_source' in component:
                    del component['slice_source']  # 移除单个来源，保留列表
                aggregated[agg_key] = component
                logger.debug(f"➕ 新构件: {agg_key}")
        
        result = list(aggregated.values())
        
        logger.info(f"✅ 构件聚合完成: {len(components)} -> {len(result)} 个构件")
        return result
    
    def _generate_component_aggregation_key(self, component: Dict[str, Any]) -> str:
        """生成构件聚合键"""
        
        # 优先使用构件ID
        component_id = component.get('component_id') or component.get('id')
        if component_id:
            return f"id_{component_id}"
        
        # 使用构件类型 + 尺寸 + 位置
        component_type = component.get('component_type') or component.get('type', 'unknown')
        
        # 尺寸信息
        dimensions = component.get('dimensions', {})
        if isinstance(dimensions, dict):
            dim_key = "_".join(f"{k}{v}" for k, v in sorted(dimensions.items()) if v)
        elif isinstance(dimensions, str):
            dim_key = dimensions.replace('x', '_').replace('×', '_')
        else:
            dim_key = ""
        
        # 位置信息（用于区分相同类型和尺寸但位置不同的构件）
        position = component.get('position', [])
        if isinstance(position, list) and len(position) >= 2:
            # 将位置量化到网格，避免微小差异
            grid_x = int(position[0] / 100) * 100  # 100像素网格
            grid_y = int(position[1] / 100) * 100
            pos_key = f"{grid_x}_{grid_y}"
        elif isinstance(position, dict):
            x = position.get('x', 0)
            y = position.get('y', 0)
            grid_x = int(x / 100) * 100
            grid_y = int(y / 100) * 100
            pos_key = f"{grid_x}_{grid_y}"
        else:
            pos_key = "nopos"
        
        return f"{component_type}_{dim_key}_{pos_key}".lower().replace(' ', '_')
    
    def _merge_component_attributes(self, existing: Dict[str, Any], new: Dict[str, Any]):
        """融合构件属性，保留更完整的信息"""
        
        # 定义重要属性
        important_attrs = [
            'dimensions', 'reinforcement', 'material', 'specifications',
            'notes', 'properties', 'details'
        ]
        
        for attr in important_attrs:
            existing_value = existing.get(attr)
            new_value = new.get(attr)
            
            # 如果现有值为空或更简单，使用新值
            if not existing_value and new_value:
                existing[attr] = new_value
            elif existing_value and new_value:
                # 如果都有值，选择更详细的
                if isinstance(existing_value, dict) and isinstance(new_value, dict):
                    # 合并字典
                    for k, v in new_value.items():
                        if not existing_value.get(k) and v:
                            existing_value[k] = v
                elif isinstance(existing_value, str) and isinstance(new_value, str):
                    # 选择更长的字符串
                    if len(new_value) > len(existing_value):
                        existing[attr] = new_value
    
    def _integrate_descriptions(self, vision_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """整合图纸说明和施工要求"""
        
        integrated = {
            'drawing_descriptions': [],
            'construction_requirements': [],
            'technical_specifications': [],
            'notes_and_remarks': [],
            'raw_text_summary': []
        }
        
        for result in vision_results:
            if not result.get('success', False):
                continue
            
            qto_data = result.get('qto_data', {})
            
            # 收集各种描述性文本
            if 'raw_text_summary' in qto_data:
                text_summary = qto_data['raw_text_summary']
                if text_summary and text_summary not in integrated['raw_text_summary']:
                    integrated['raw_text_summary'].append(text_summary)
            
            # 收集图纸说明
            if 'drawing_notes' in qto_data:
                notes = qto_data['drawing_notes']
                if notes and notes not in integrated['drawing_descriptions']:
                    integrated['drawing_descriptions'].append(notes)
            
            # 收集施工要求
            if 'construction_notes' in qto_data:
                const_notes = qto_data['construction_notes']
                if const_notes and const_notes not in integrated['construction_requirements']:
                    integrated['construction_requirements'].append(const_notes)
            
            # 收集技术规格
            if 'technical_specs' in qto_data:
                tech_specs = qto_data['technical_specs']
                if tech_specs and tech_specs not in integrated['technical_specifications']:
                    integrated['technical_specifications'].append(tech_specs)
        
        # 将列表转换为长段文本
        for key in integrated:
            if integrated[key]:
                integrated[key] = '\n\n'.join(integrated[key])
            else:
                integrated[key] = ""
        
        return integrated
    
    def _generate_component_summary(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成构件汇总统计"""
        
        if not components:
            return {}
        
        summary = {}
        
        # 按类型分组统计
        type_groups = {}
        for component in components:
            comp_type = component.get('component_type') or component.get('type', 'unknown')
            if comp_type not in type_groups:
                type_groups[comp_type] = []
            type_groups[comp_type].append(component)
        
        # 为每种类型生成汇总
        for comp_type, comps in type_groups.items():
            total_quantity = sum(comp.get('quantity', 1) for comp in comps)
            unique_specifications = set()
            
            for comp in comps:
                # 收集规格
                if 'dimensions' in comp:
                    dims = comp['dimensions']
                    if isinstance(dims, dict):
                        spec = "_".join(f"{k}:{v}" for k, v in dims.items() if v)
                    else:
                        spec = str(dims)
                    unique_specifications.add(spec)
            
            summary[comp_type] = {
                '数量': total_quantity,
                '种类': len(comps),
                '规格': list(unique_specifications) if unique_specifications else []
            }
        
        # 总计
        summary['总计'] = {
            '构件类型数': len(type_groups),
            '构件总数': len(components),
            '总数量': sum(comp.get('quantity', 1) for comp in components)
        }
        
        return summary
    
    def _calculate_component_distribution(self, components: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算构件类型分布"""
        
        distribution = {}
        
        for component in components:
            comp_type = component.get('component_type') or component.get('type', 'unknown')
            quantity = component.get('quantity', 1)
            
            if comp_type in distribution:
                distribution[comp_type] += quantity
            else:
                distribution[comp_type] = quantity
        
        return distribution
    
    def _generate_merge_metadata(self, 
                               vision_results: List[Dict[str, Any]], 
                               total_merged_components: int, 
                               start_time: float) -> Dict[str, Any]:
        """生成合并元数据"""
        
        successful_results = [r for r in vision_results if r.get('success', False)]
        
        return {
            'merge_strategy': 'component_aggregation_and_attribute_fusion',
            'coordinate_restoration': True,
            'component_deduplication': True,
            'attribute_fusion': True,
            'processing_info': {
                'total_slices': len(vision_results),
                'successful_slices': len(successful_results),
                'success_rate': len(successful_results) / len(vision_results) if vision_results else 0,
                'total_components_before_merge': sum(
                    len(r.get('qto_data', {}).get('components', [])) 
                    for r in successful_results
                ),
                'total_components_after_merge': total_merged_components,
                'merge_time': time.time() - start_time
            },
            'merge_algorithms': {
                'component_key_generation': 'id_or_type_dimension_position',
                'coordinate_restoration': 'slice_offset_adjustment',
                'attribute_fusion': 'completeness_based_selection',
                'quantity_aggregation': 'sum_based'
            }
        }
    
    async def save_vision_full_result(self, 
                                    vision_full_result: VisionFullResult, 
                                    drawing_id: int) -> Dict[str, Any]:
        """保存Vision全图合并结果到存储"""
        
        if not self.storage_service:
            logger.warning("存储服务不可用，跳过Vision全图结果保存")
            return {"error": "Storage service not available"}
        
        try:
            # 将结果转换为可序列化的字典
            result_data = {
                'task_id': vision_full_result.task_id,
                'original_image_info': vision_full_result.original_image_info,
                'total_slices': vision_full_result.total_slices,
                'successful_slices': vision_full_result.successful_slices,
                
                'project_info': vision_full_result.project_info,
                'merged_components': vision_full_result.merged_components,
                'component_summary': vision_full_result.component_summary,
                'integrated_descriptions': vision_full_result.integrated_descriptions,
                
                'total_components': vision_full_result.total_components,
                'component_types_distribution': vision_full_result.component_types_distribution,
                
                'merge_metadata': vision_full_result.merge_metadata,
                'timestamp': vision_full_result.timestamp,
                
                'format_version': '1.0',
                'generated_by': 'VisionResultMerger'
            }
            
            logger.info(f"💾 准备保存Vision全图合并结果: {len(vision_full_result.merged_components)} 个构件")
            
            # 生成唯一的结果文件名
            import uuid
            result_uuid = str(uuid.uuid4())
            
            # 同时保存两个文件：固定名称和UUID名称
            save_results = []
            
            # 1. 保存固定名称文件（便于下载）
            s3_key_fixed = f"llm_results/{drawing_id}/vision_full.json"
            result_upload_fixed = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key_fixed,
                content_type="application/json"
            )
            
            if result_upload_fixed.get("success"):
                logger.info(f"✅ S3主存储上传成功: vision_full.json")
                save_results.append({
                    "type": "fixed_name",
                    "success": True,
                    "s3_url": result_upload_fixed.get("final_url"),
                    "s3_key": s3_key_fixed
                })
            
            # 2. 保存UUID名称文件（确保唯一性）
            s3_key_uuid = f"llm_results/{drawing_id}/{result_uuid}.json"
            result_upload_uuid = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key_uuid,
                content_type="application/json"
            )
            
            if result_upload_uuid.get("success"):
                logger.info(f"✅ Vision全图合并结果已保存: {result_upload_uuid.get('final_url')}")
                save_results.append({
                    "type": "uuid_name", 
                    "success": True,
                    "s3_url": result_upload_uuid.get("final_url"),
                    "s3_key": s3_key_uuid
                })
            
            # 返回综合结果
            if save_results:
                return {
                    "success": True,
                    "s3_url": save_results[-1]["s3_url"],  # 使用最后一个成功的URL
                    "s3_key": save_results[-1]["s3_key"],
                    "storage_method": result_upload_uuid.get("storage_method", "sealos"),
                    "all_saves": save_results,
                    "components_count": len(vision_full_result.merged_components)
                }
            else:
                logger.error("❌ 所有存储尝试都失败了")
                return {"success": False, "error": "All storage attempts failed"}
            
        except Exception as e:
            logger.error(f"保存Vision全图合并结果异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)} 