"""
结果合并服务
整合OCR切片结果和Vision分析结果的合并功能
"""

import json
import time
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ResultMergerService:
    """结果合并服务"""
    
    def __init__(self, storage_service=None):
        self.storage_service = storage_service
    
    def merge_ocr_slice_results(self, 
                              slice_results: List[Dict[str, Any]], 
                              slice_coordinate_map: Dict[str, Any],
                              original_image_info: Dict[str, Any],
                              task_id: str,
                              drawing_id: int) -> Dict[str, Any]:
        """
        合并OCR切片扫描结果
        生成 ocr_full.json - 全图文本拼接，按位置+box拼合
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
                restored_region = self._restore_text_coordinates(
                    region, offset_x, offset_y, slice_info, i
                )
                if restored_region:
                    all_text_regions.append(restored_region)
        
        # 2. 去除重叠区域的重复文本
        deduplicated_regions = self._remove_duplicate_text(all_text_regions)
        
        # 3. 按位置排序和拼接
        positioned_text = self._organize_text_by_position(
            deduplicated_regions, original_image_info
        )
        
        # 4. 生成完整文本内容
        full_text_content = self._generate_full_text(positioned_text)
        
        # 5. 生成OCR全图结果
        ocr_full_result = {
            'task_id': task_id,
            'original_image_info': original_image_info,
            'total_slices': len(slice_results),
            'successful_slices': successful_slices,
            'success_rate': successful_slices / len(slice_results) if slice_results else 0,
            
            # 合并后的文本内容
            'all_text_regions': deduplicated_regions,
            'full_text_content': full_text_content,
            'text_by_position': positioned_text,
            
            # 统计信息
            'total_text_regions': len(deduplicated_regions),
            'total_characters': sum(len(region.get('text', '')) for region in deduplicated_regions),
            'average_confidence': self._calculate_avg_confidence(deduplicated_regions),
            
            # 处理信息
            'merge_metadata': {
                'merge_strategy': 'position_and_box_based',
                'coordinate_restoration': True,
                'duplicate_removal': True,
                'position_organization': True,
                'merge_time': time.time() - start_time
            },
            'timestamp': time.time(),
            'format_version': '1.0',
            'generated_by': 'ResultMergerService'
        }
        
        # 6. 保存到存储
        save_result = self._save_ocr_full_result(ocr_full_result, drawing_id)
        
        logger.info(f"✅ OCR切片合并完成: {len(all_text_regions)} -> {len(deduplicated_regions)} 个文本区域")
        return {
            'success': True,
            'ocr_full_result': ocr_full_result,
            'storage_result': save_result
        }
    
    def merge_vision_analysis_results(self, 
                                    vision_results: List[Dict[str, Any]], 
                                    slice_coordinate_map: Dict[str, Any],
                                    original_image_info: Dict[str, Any],
                                    task_id: str,
                                    drawing_id: int) -> Dict[str, Any]:
        """
        合并Vision分析结果
        生成 vision_full.json - 结构化清单，便于导出成表格、报告
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
        
        # 5. 生成Vision全图结果
        vision_full_result = {
            'task_id': task_id,
            'original_image_info': original_image_info,
            'total_slices': len(vision_results),
            'successful_slices': len([r for r in vision_results if r.get('success', False)]),
            
            # 项目信息（最完整的一份）
            'project_info': project_info,
            
            # 合并后的构件信息
            'merged_components': merged_components,
            'component_summary': component_summary,
            
            # 整合的图纸说明和施工要求
            'integrated_descriptions': integrated_descriptions,
            
            # 统计信息
            'total_components': len(merged_components),
            'component_types_distribution': self._calculate_component_distribution(merged_components),
            
            # 处理信息
            'merge_metadata': {
                'merge_strategy': 'component_aggregation_and_attribute_fusion',
                'coordinate_restoration': True,
                'component_deduplication': True,
                'attribute_fusion': True,
                'merge_time': time.time() - start_time
            },
            'timestamp': time.time(),
            'format_version': '1.0',
            'generated_by': 'ResultMergerService'
        }
        
        # 6. 保存到存储
        save_result = self._save_vision_full_result(vision_full_result, drawing_id)
        
        logger.info(f"✅ Vision分析结果合并完成: {len(merged_components)} 个构件")
        return {
            'success': True,
            'vision_full_result': vision_full_result,
            'storage_result': save_result
        }
    
    def _restore_text_coordinates(self, 
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
        
        # 添加切片来源信息
        restored_region['slice_source'] = {
            'slice_index': slice_index,
            'slice_id': slice_info.get('slice_id', f'slice_{slice_index}'),
            'offset': (offset_x, offset_y)
        }
        
        return restored_region
    
    def _remove_duplicate_text(self, text_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重叠区域的重复文本"""
        
        if not text_regions:
            return []
        
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
                    break
            
            if not is_duplicate:
                deduplicated.append(current_region)
        
        return deduplicated
    
    def _organize_text_by_position(self, 
                                 text_regions: List[Dict[str, Any]], 
                                 original_image_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """按位置组织文本"""
        
        image_width = original_image_info.get('width', 0)
        image_height = original_image_info.get('height', 0)
        
        # 网格分组
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
                    'grid': (grid_x, grid_y)
                }
                
                positioned_text.append(positioned_region)
        
        # 按位置排序（从上到下，从左到右）
        positioned_text.sort(key=lambda x: (
            x['position_info']['grid'][1],  # Y网格优先
            x['position_info']['grid'][0]   # 然后X网格
        ))
        
        return positioned_text
    
    def _generate_full_text(self, positioned_text: List[Dict[str, Any]]) -> str:
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
    
    def _merge_project_info(self, vision_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并项目信息，保留最完整的一份"""
        
        all_project_info = []
        
        for result in vision_results:
            if not result.get('success', False):
                continue
                
            qto_data = result.get('qto_data', {})
            
            # 获取项目信息
            project_info = {}
            
            # 从各个字段中提取
            for key in ['drawing_info', 'project_analysis', 'project_name', 'company_name', 
                       'drawing_name', 'scale', 'drawing_number']:
                if key in qto_data and qto_data[key]:
                    if isinstance(qto_data[key], dict):
                        project_info.update(qto_data[key])
                    else:
                        project_info[key] = qto_data[key]
            
            if project_info:
                all_project_info.append(project_info)
        
        if not all_project_info:
            return {}
        
        # 选择最完整的项目信息
        best_project_info = max(all_project_info, key=lambda x: (
            len([v for v in x.values() if v and v != 'Unknown' and v != 'N/A']),
            len(x)
        ))
        
        return best_project_info
    
    def _merge_and_restore_components(self, 
                                    vision_results: List[Dict[str, Any]], 
                                    slice_coordinate_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """合并并还原构件坐标"""
        
        all_components = []
        
        for i, result in enumerate(vision_results):
            if not result.get('success', False):
                continue
            
            qto_data = result.get('qto_data', {})
            components = qto_data.get('components', [])
            
            if not components:
                continue
            
            # 获取该切片的坐标信息
            slice_info = slice_coordinate_map.get(i, {})
            offset_x = slice_info.get('offset_x', 0)
            offset_y = slice_info.get('offset_y', 0)
            
            # 还原每个构件的坐标
            for component in components:
                restored_component = self._restore_component_coordinates(
                    component, offset_x, offset_y, slice_info, i
                )
                if restored_component:
                    all_components.append(restored_component)
        
        # 按构件ID和属性聚合去重
        merged_components = self._aggregate_components(all_components)
        
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
        
        # 还原各种坐标信息
        for coord_field in ['position', 'bbox', 'center']:
            if coord_field in component:
                coord_value = component[coord_field]
                if isinstance(coord_value, list) and len(coord_value) >= 2:
                    if coord_field == 'bbox' and len(coord_value) >= 4:
                        restored_component[coord_field] = [
                            coord_value[0] + offset_x,  # x1
                            coord_value[1] + offset_y,  # y1
                            coord_value[2] + offset_x,  # x2
                            coord_value[3] + offset_y   # y2
                        ]
                    else:
                        restored_component[coord_field] = [
                            coord_value[0] + offset_x,
                            coord_value[1] + offset_y
                        ]
                elif isinstance(coord_value, dict):
                    if 'x' in coord_value and 'y' in coord_value:
                        restored_component[coord_field] = {
                            'x': coord_value['x'] + offset_x,
                            'y': coord_value['y'] + offset_y
                        }
        
        # 添加切片来源信息
        restored_component['slice_source'] = {
            'slice_index': slice_index,
            'slice_id': slice_info.get('slice_id', f'slice_{slice_index}'),
            'offset': (offset_x, offset_y)
        }
        
        return restored_component
    
    def _aggregate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按构件ID或坐标聚合重复构件"""
        
        if not components:
            return []
        
        # 构件聚合字典
        aggregated = {}
        
        for component in components:
            # 生成聚合键
            agg_key = self._generate_component_key(component)
            
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
                
            else:
                # 新构件
                component['slice_sources'] = [component.get('slice_source', {})]
                if 'slice_source' in component:
                    del component['slice_source']
                aggregated[agg_key] = component
        
        return list(aggregated.values())
    
    def _generate_component_key(self, component: Dict[str, Any]) -> str:
        """生成构件聚合键"""
        
        # 优先使用构件ID
        component_id = component.get('component_id') or component.get('id')
        if component_id:
            return f"id_{component_id}"
        
        # 使用构件类型 + 尺寸 + 位置网格
        component_type = component.get('component_type') or component.get('type', 'unknown')
        
        # 尺寸信息
        dimensions = component.get('dimensions', {})
        if isinstance(dimensions, dict):
            dim_key = "_".join(f"{k}{v}" for k, v in sorted(dimensions.items()) if v)
        else:
            dim_key = str(dimensions).replace('x', '_').replace('×', '_')
        
        # 位置网格（避免微小差异）
        position = component.get('position', [])
        if isinstance(position, list) and len(position) >= 2:
            grid_x = int(position[0] / 100) * 100  # 100像素网格
            grid_y = int(position[1] / 100) * 100
            pos_key = f"{grid_x}_{grid_y}"
        else:
            pos_key = "nopos"
        
        return f"{component_type}_{dim_key}_{pos_key}".lower().replace(' ', '_')
    
    def _integrate_descriptions(self, vision_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """整合图纸说明和施工要求"""
        
        integrated = {
            'drawing_descriptions': [],
            'construction_requirements': [],
            'technical_specifications': [],
            'raw_text_summaries': []
        }
        
        for result in vision_results:
            if not result.get('success', False):
                continue
            
            qto_data = result.get('qto_data', {})
            
            # 收集各种描述性文本
            for key, target_list in [
                ('raw_text_summary', 'raw_text_summaries'),
                ('drawing_notes', 'drawing_descriptions'),
                ('construction_notes', 'construction_requirements'),
                ('technical_specs', 'technical_specifications')
            ]:
                if key in qto_data and qto_data[key]:
                    text = qto_data[key]
                    if text not in integrated[target_list]:
                        integrated[target_list].append(text)
        
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
            summary[comp_type] = {
                '数量': total_quantity,
                '种类': len(comps)
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
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0
        
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
    
    def _calculate_avg_confidence(self, text_regions: List[Dict[str, Any]]) -> float:
        """计算平均置信度"""
        if not text_regions:
            return 0.0
        
        confidences = [region.get('confidence', 0) for region in text_regions]
        return sum(confidences) / len(confidences) if confidences else 0
    
    def _save_ocr_full_result(self, result_data: Dict[str, Any], drawing_id: int) -> Dict[str, Any]:
        """保存OCR全图合并结果，包含JSON、RAW、TXT三种格式"""
        
        if not self.storage_service:
            return {"success": False, "error": "Storage service not available"}
        
        try:
            # 1. 保存JSON格式的完整结果
            json_s3_key = f"ocr_results/{drawing_id}/ocr_full.json"
            json_result = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=json_s3_key,
                content_type="application/json"
            )
            
            # 2. 生成并保存RAW格式（结构化文本，保持位置信息）
            raw_content = self._generate_raw_format(result_data)
            raw_s3_key = f"ocr_results/{drawing_id}/ocr_full.raw"
            raw_result = self.storage_service.upload_content_sync(
                content=raw_content,
                s3_key=raw_s3_key,
                content_type="text/plain"
            )
            
            # 3. 生成并保存TXT格式（纯文本，按阅读顺序）
            txt_content = self._generate_txt_format(result_data)
            txt_s3_key = f"ocr_results/{drawing_id}/ocr_full.txt"
            txt_result = self.storage_service.upload_content_sync(
                content=txt_content,
                s3_key=txt_s3_key,
                content_type="text/plain"
            )
            
            # 汇总保存结果
            save_results = {
                "json": json_result,
                "raw": raw_result,
                "txt": txt_result
            }
            
            success_count = sum(1 for result in save_results.values() if result.get("success", False))
            
            if success_count > 0:
                logger.info(f"✅ OCR全图合并结果已保存: {success_count}/3 种格式成功")
                return {
                    "success": True,
                    "formats_saved": success_count,
                    "results": save_results,
                    "primary_url": json_result.get("final_url") if json_result.get("success") else None
                }
            else:
                return {"success": False, "error": "所有格式保存均失败", "results": save_results}
                
        except Exception as e:
            logger.error(f"保存OCR全图合并结果失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_raw_format(self, result_data: Dict[str, Any]) -> str:
        """生成RAW格式内容（结构化文本，保持位置和边界框信息）"""
        
        lines = []
        lines.append("=" * 80)
        lines.append("OCR全图重构结果 - RAW格式")
        lines.append("=" * 80)
        lines.append(f"任务ID: {result_data.get('task_id', 'N/A')}")
        lines.append(f"生成时间: {result_data.get('timestamp', 'N/A')}")
        lines.append(f"总文本区域: {result_data.get('total_text_regions', 0)}")
        lines.append(f"总字符数: {result_data.get('total_characters', 0)}")
        lines.append(f"平均置信度: {result_data.get('average_confidence', 0):.2f}")
        lines.append("")
        
        # 按位置组织的文本区域
        text_by_position = result_data.get('text_by_position', [])
        if text_by_position:
            lines.append("按位置组织的文本内容:")
            lines.append("-" * 40)
            
            for i, position_group in enumerate(text_by_position):
                lines.append(f"\n位置区域 {i+1}:")
                regions = position_group.get('regions', [])
                
                for region in regions:
                    bbox = region.get('bbox', [])
                    confidence = region.get('confidence', 0)
                    text = region.get('text', '').strip()
                    
                    if text:
                        bbox_str = f"[{','.join(map(str, bbox))}]" if bbox else "[无坐标]"
                        lines.append(f"  坐标{bbox_str} 置信度:{confidence:.2f} | {text}")
        
        lines.append("\n" + "=" * 80)
        return '\n'.join(lines)
    
    def _generate_txt_format(self, result_data: Dict[str, Any]) -> str:
        """生成TXT格式内容（纯文本，按阅读顺序）"""
        
        lines = []
        lines.append("OCR全图重构结果 - 纯文本格式")
        lines.append("=" * 50)
        lines.append(f"任务ID: {result_data.get('task_id', 'N/A')}")
        lines.append(f"识别文本区域数: {result_data.get('total_text_regions', 0)}")
        lines.append("")
        
        # 使用full_text_content，这是按位置排序的完整文本
        full_text = result_data.get('full_text_content', '')
        if full_text:
            lines.append("识别的文本内容:")
            lines.append("-" * 30)
            lines.append(full_text)
        else:
            # 如果没有full_text_content，从all_text_regions中提取
            all_regions = result_data.get('all_text_regions', [])
            if all_regions:
                lines.append("识别的文本内容:")
                lines.append("-" * 30)
                
                # 按y坐标排序，然后按x坐标排序
                sorted_regions = sorted(all_regions, key=lambda r: (
                    r.get('bbox', [0, 0, 0, 0])[1],  # y坐标
                    r.get('bbox', [0, 0, 0, 0])[0]   # x坐标
                ))
                
                for region in sorted_regions:
                    text = region.get('text', '').strip()
                    if text:
                        lines.append(text)
        
        return '\n'.join(lines)
    
    def _save_vision_full_result(self, result_data: Dict[str, Any], drawing_id: int) -> Dict[str, Any]:
        """保存Vision全图合并结果"""
        
        if not self.storage_service:
            return {"success": False, "error": "Storage service not available"}
        
        try:
            s3_key = f"llm_results/{drawing_id}/vision_full.json"
            result_upload = self.storage_service.upload_content_sync(
                content=json.dumps(result_data, ensure_ascii=False, indent=2),
                s3_key=s3_key,
                content_type="application/json"
            )
            
            if result_upload.get("success"):
                logger.info(f"✅ Vision全图合并结果已保存: {result_upload.get('final_url')}")
                return {
                    "success": True,
                    "s3_url": result_upload.get("final_url"),
                    "s3_key": s3_key
                }
            else:
                return {"success": False, "error": result_upload.get('error')}
                
        except Exception as e:
            logger.error(f"保存Vision全图合并结果失败: {e}")
            return {"success": False, "error": str(e)} 