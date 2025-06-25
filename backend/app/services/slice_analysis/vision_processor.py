#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision处理器
从enhanced_grid_slice_analyzer.py中提取的Vision分析功能
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional

from ..enhanced_slice_models import EnhancedSliceInfo
from ..ai_analyzer import AIAnalyzerService

logger = logging.getLogger(__name__)

class VisionProcessor:
    """Vision处理器 - 负责图像视觉分析"""
    
    def __init__(self):
        # 初始化AI分析器
        self.ai_analyzer = None
        try:
            self.ai_analyzer = AIAnalyzerService()
        except Exception as e:
            logger.warning(f"⚠️ AI分析器初始化失败: {e}")
    
    def analyze_slices_with_enhanced_vision(self, enhanced_slices: List[EnhancedSliceInfo], 
                                           drawing_info: Dict[str, Any], 
                                           task_id: str) -> Dict[str, Any]:
        """使用增强Vision分析切片"""
        try:
            if not self.ai_analyzer:
                return {"success": False, "error": "AI分析器未初始化"}
            
            vision_results = []
            successful_count = 0
            failed_count = 0
            
            for slice_info in enhanced_slices:
                # 生成基础Vision提示
                basic_prompt = self._generate_basic_vision_prompt(slice_info, drawing_info)
                
                # 执行单切片Vision分析
                vision_task_id = f"{task_id}_vision_{slice_info.slice_id}"
                slice_result = self._analyze_single_slice_with_vision(
                    slice_info, basic_prompt, vision_task_id
                )
                
                if slice_result.get("success"):
                    vision_results.append(slice_result)
                    successful_count += 1
                    logger.info(f"✅ Vision分析成功: {slice_info.slice_id}")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Vision分析失败: {slice_info.slice_id} - {slice_result.get('error', '未知错误')}")
            
            logger.info(f"✅ Vision分析完成: 成功 {successful_count} 个，失败 {failed_count} 个")
            
            return {
                "success": True,
                "vision_results": vision_results,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "total_analyzed": len(enhanced_slices)
            }
            
        except Exception as e:
            logger.error(f"❌ Vision分析过程发生错误: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_basic_vision_prompt(self, slice_info: EnhancedSliceInfo, 
                                     drawing_info: Dict[str, Any]) -> str:
        """生成基础Vision分析提示"""
        
        # 基础提示模板
        base_prompt = f"""
# 建筑图纸切片分析任务

## 图纸信息
- 项目名称: {drawing_info.get('project_name', '未知项目')}
- 图纸类型: {drawing_info.get('drawing_type', '建筑施工图')}
- 切片编号: {slice_info.slice_id}

## 分析目标
请仔细分析这个图纸切片，识别其中的建筑构件和相关信息。

## 重点关注
1. **构件编号** - 如 KZ1, L1, B1 等标注
2. **尺寸标注** - 长×宽×高 或截面尺寸
3. **配筋信息** - 钢筋规格和配置
4. **材料等级** - 混凝土强度等级等
5. **位置关系** - 构件在轴线上的位置

## 输出要求
请按照JSON格式输出识别结果，包含：
- 构件编号和类型
- 尺寸信息
- 配筋详情（如有）
- 位置坐标（像素坐标）
- 置信度评估
        """
        
        # 如果有OCR增强提示，添加到基础提示中
        if hasattr(slice_info, 'enhanced_prompt') and slice_info.enhanced_prompt:
            base_prompt += f"\n\n## OCR辅助信息\n{slice_info.enhanced_prompt}"
        
        return base_prompt.strip()
    
    def _analyze_single_slice_with_vision(self, slice_info: EnhancedSliceInfo, 
                                         prompt: str, vision_task_id: str) -> Dict[str, Any]:
        """分析单个切片的Vision内容"""
        try:
            # 构建Vision分析请求
            vision_request = {
                "image_path": slice_info.slice_path,
                "prompt": prompt,
                "task_id": vision_task_id,
                "analysis_type": "structural_component_detection"
            }
            
            # 调用AI分析器进行Vision分析
            analysis_result = self.ai_analyzer.analyze_image_with_vision(
                image_path=slice_info.slice_path,
                prompt=prompt,
                task_id=vision_task_id
            )
            
            if not analysis_result.get("success"):
                return {
                    "success": False,
                    "error": analysis_result.get("error", "Vision分析失败"),
                    "slice_id": slice_info.slice_id
                }
            
            # 解析Vision分析结果
            vision_data = analysis_result.get("analysis_result", {})
            components = self._parse_vision_components(vision_data, slice_info)
            
            return {
                "success": True,
                "slice_id": slice_info.slice_id,
                "vision_data": vision_data,
                "components": components,
                "component_count": len(components)
            }
            
        except Exception as e:
            logger.error(f"❌ 单切片Vision分析失败 {slice_info.slice_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "slice_id": slice_info.slice_id
            }
    
    def _parse_vision_components(self, vision_data: Dict[str, Any], 
                                slice_info: EnhancedSliceInfo) -> List[Dict[str, Any]]:
        """解析Vision分析结果中的构件信息"""
        try:
            components = []
            
            # 尝试从不同可能的结构中提取构件信息
            potential_sources = [
                vision_data.get("components", []),
                vision_data.get("structural_components", []),
                vision_data.get("detected_components", []),
                vision_data.get("elements", [])
            ]
            
            for source in potential_sources:
                if isinstance(source, list) and source:
                    for item in source:
                        if isinstance(item, dict):
                            component = self._parse_single_component(item, slice_info)
                            if component:
                                components.append(component)
                    break  # 找到有效数据源后退出
            
            # 如果没有找到结构化的构件数据，尝试从原始响应中解析
            if not components and vision_data:
                component = self._parse_unstructured_response(vision_data, slice_info)
                if component:
                    components.append(component)
            
            logger.debug(f"从切片 {slice_info.slice_id} 解析出 {len(components)} 个构件")
            return components
            
        except Exception as e:
            logger.warning(f"⚠️ 解析Vision构件时出错: {e}")
            return []
    
    def _parse_single_component(self, component_data: Dict[str, Any], 
                               slice_info: EnhancedSliceInfo) -> Optional[Dict[str, Any]]:
        """解析单个构件数据"""
        try:
            # 提取基本信息
            component_id = component_data.get("id") or component_data.get("component_id") or ""
            component_type = component_data.get("type") or component_data.get("component_type") or ""
            
            if not component_id and not component_type:
                return None
            
            # 构建标准化的构件信息
            parsed_component = {
                "component_id": component_id,
                "component_type": component_type,
                "slice_id": slice_info.slice_id,
                "source": "vision_analysis"
            }
            
            # 提取尺寸信息
            dimensions = component_data.get("dimensions") or component_data.get("size")
            if dimensions:
                parsed_component["dimensions"] = self._parse_dimensions(dimensions)
            
            # 提取位置信息
            position = component_data.get("position") or component_data.get("bbox") or component_data.get("location")
            if position:
                parsed_component["position"] = self._parse_position(position)
            
            # 提取配筋信息
            reinforcement = component_data.get("reinforcement") or component_data.get("steel")
            if reinforcement:
                parsed_component["reinforcement"] = self._parse_reinforcement(reinforcement)
            
            # 提取材料信息
            material = component_data.get("material") or component_data.get("concrete")
            if material:
                parsed_component["material"] = material
            
            # 提取置信度
            confidence = component_data.get("confidence", 0.0)
            parsed_component["confidence"] = float(confidence) if confidence else 0.0
            
            return parsed_component
            
        except Exception as e:
            logger.warning(f"⚠️ 解析单个构件失败: {e}")
            return None
    
    def _parse_unstructured_response(self, vision_data: Dict[str, Any], 
                                   slice_info: EnhancedSliceInfo) -> Optional[Dict[str, Any]]:
        """解析非结构化的Vision响应"""
        try:
            # 尝试从文本描述中提取信息
            description = vision_data.get("description") or vision_data.get("analysis") or ""
            
            if not description:
                return None
            
            # 创建基础构件信息
            component = {
                "component_id": f"vision_{slice_info.slice_id}",
                "component_type": "未分类构件",
                "slice_id": slice_info.slice_id,
                "source": "vision_analysis",
                "description": description,
                "confidence": 0.5  # 较低的置信度
            }
            
            return component
            
        except Exception as e:
            logger.warning(f"⚠️ 解析非结构化响应失败: {e}")
            return None
    
    def _parse_dimensions(self, dimensions_data: Any) -> Dict[str, Any]:
        """解析尺寸信息"""
        try:
            if isinstance(dimensions_data, dict):
                return dimensions_data
            elif isinstance(dimensions_data, str):
                # 尝试解析字符串格式的尺寸
                dims = {}
                if 'x' in dimensions_data.lower() or '×' in dimensions_data:
                    parts = dimensions_data.replace('×', 'x').split('x')
                    if len(parts) >= 2:
                        dims["width"] = parts[0].strip()
                        dims["height"] = parts[1].strip()
                        if len(parts) >= 3:
                            dims["length"] = parts[2].strip()
                return dims
            else:
                return {"raw": str(dimensions_data)}
        except Exception as e:
            logger.warning(f"⚠️ 解析尺寸信息失败: {e}")
            return {}
    
    def _parse_position(self, position_data: Any) -> Dict[str, Any]:
        """解析位置信息"""
        try:
            if isinstance(position_data, dict):
                return position_data
            elif isinstance(position_data, list) and len(position_data) >= 4:
                return {
                    "x": position_data[0],
                    "y": position_data[1],
                    "width": position_data[2],
                    "height": position_data[3]
                }
            else:
                return {"raw": str(position_data)}
        except Exception as e:
            logger.warning(f"⚠️ 解析位置信息失败: {e}")
            return {}
    
    def _parse_reinforcement(self, reinforcement_data: Any) -> Dict[str, Any]:
        """解析配筋信息"""
        try:
            if isinstance(reinforcement_data, dict):
                return reinforcement_data
            elif isinstance(reinforcement_data, str):
                return {"description": reinforcement_data}
            else:
                return {"raw": str(reinforcement_data)}
        except Exception as e:
            logger.warning(f"⚠️ 解析配筋信息失败: {e}")
            return {} 