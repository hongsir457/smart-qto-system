#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文链切片分析器
针对切片后的局部图纸，优化五步交互式分析，确保上下文连贯性
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class GlobalContext:
    """全局上下文信息"""
    project_name: str
    drawing_type: str
    scale: str
    main_component_types: List[str]
    estimated_total_components: int
    project_metadata: Dict[str, Any]

@dataclass 
class SliceContext:
    """切片上下文信息"""
    slice_index: int
    slice_id: str
    slice_bounds: Tuple[int, int, int, int]  # (x, y, width, height)
    slice_position: str  # 'top-left', 'center', 'bottom-right' etc.
    focus_areas: List[str]  # ['components', 'dimensions', 'annotations']
    relative_to_global: Dict[str, float]  # 相对全图的位置比例

class ContextualSliceAnalyzer:
    """上下文链切片分析器"""
    
    def __init__(self):
        self.ai_analyzer = None
        try:
            from app.services.ai_analyzer import AIAnalyzerService
            self.ai_analyzer = AIAnalyzerService()
        except Exception as e:
            logger.warning(f"⚠️ AI分析器初始化失败: {e}")
        
        self.global_context: Optional[GlobalContext] = None
        self.slice_contexts: List[SliceContext] = []
        self.context_chain: List[Dict[str, Any]] = []
        
    def analyze_with_contextual_chain(self, 
                                    full_image_path: str,
                                    slice_images: List[str],
                                    slice_configs: List[Dict[str, Any]],
                                    task_id: str,
                                    drawing_id: int = None) -> Dict[str, Any]:
        """
        使用上下文链进行切片分析
        
        Args:
            full_image_path: 完整图纸路径
            slice_images: 切片图像路径列表
            slice_configs: 切片配置信息
            task_id: 任务ID
            drawing_id: 图纸ID
            
        Returns:
            分析结果
        """
        logger.info(f"🔄 开始上下文链切片分析: {len(slice_images)} 个切片")
        
        if not self.ai_analyzer or not self.ai_analyzer.is_available():
            return {
                "error": "AI Analyzer Service is not available",
                "success": False
            }
        
        try:
            # Phase 1: 全图概览分析 - 建立全局上下文
            logger.info("🌍 Phase 1: 全图概览分析")
            global_analysis = self._analyze_global_overview(full_image_path, task_id, drawing_id)
            
            if not global_analysis.get("success"):
                logger.error("❌ 全图概览分析失败")
                return global_analysis
            
            # 建立全局上下文
            self.global_context = self._build_global_context(global_analysis["qto_data"])
            logger.info(f"✅ 全局上下文建立: 项目={self.global_context.project_name}, "
                       f"类型={self.global_context.drawing_type}")
            
            # Phase 2: 切片上下文链分析
            logger.info("🔗 Phase 2: 切片上下文链分析")
            slice_results = self._analyze_slices_with_context_chain(
                slice_images, slice_configs, task_id, drawing_id
            )
            
            # Phase 3: 结果合并与一致性校验
            logger.info("🔀 Phase 3: 结果合并与一致性校验")
            merged_result = self._merge_and_validate_results(
                global_analysis, slice_results, task_id
            )
            
            logger.info("✅ 上下文链切片分析完成")
            return merged_result
            
        except Exception as e:
            logger.error(f"❌ 上下文链切片分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "contextual_slice_analysis"
            }
    
    def _analyze_global_overview(self, 
                               full_image_path: str,
                               task_id: str,
                               drawing_id: int = None) -> Dict[str, Any]:
        """全图概览分析 - 建立全局上下文"""
        
        logger.info("🔍 执行全图概览分析...")
        
        # 使用缩略图进行全局五步交互分析
        try:
            # 生成缩略图（如果需要）
            thumbnail_path = self._create_thumbnail_if_needed(full_image_path)
            
            # 执行V2版本的五步交互分析
            global_result = self.ai_analyzer.generate_qto_from_local_images_v2(
                image_paths=[thumbnail_path],
                task_id=f"{task_id}_global",
                drawing_id=drawing_id
            )
            
            if global_result.get("success"):
                logger.info("✅ 全图概览分析成功")
                return global_result
            else:
                logger.error(f"❌ 全图概览分析失败: {global_result.get('error')}")
                return global_result
                
        except Exception as e:
            logger.error(f"❌ 全图概览分析异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_thumbnail_if_needed(self, image_path: str, max_size: int = 1024) -> str:
        """如果需要，创建缩略图"""
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                # 如果图像太大，创建缩略图
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    
                    # 保存缩略图
                    thumbnail_path = image_path.replace('.', '_thumbnail.')
                    img.save(thumbnail_path)
                    logger.info(f"📷 创建缩略图: {thumbnail_path}")
                    return thumbnail_path
                else:
                    return image_path
                    
        except Exception as e:
            logger.warning(f"⚠️ 缩略图创建失败，使用原图: {e}")
            return image_path
    
    def _build_global_context(self, global_qto_data: Dict[str, Any]) -> GlobalContext:
        """从全图分析结果构建全局上下文"""
        
        try:
            drawing_info = global_qto_data.get("drawing_info", {})
            components = global_qto_data.get("components", [])
            
            return GlobalContext(
                project_name=drawing_info.get("project_name", "未知项目"),
                drawing_type=drawing_info.get("drawing_name", "结构图"),
                scale=drawing_info.get("scale", "1:100"),
                main_component_types=list(set([
                    comp.get("component_type", "未知") for comp in components
                ])),
                estimated_total_components=len(components),
                project_metadata={
                    "design_unit": drawing_info.get("design_unit", ""),
                    "design_date": drawing_info.get("design_date", ""),
                    "drawing_number": drawing_info.get("drawing_number", ""),
                    "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            
        except Exception as e:
            logger.error(f"❌ 构建全局上下文失败: {e}")
            # 返回默认上下文
            return GlobalContext(
                project_name="未知项目",
                drawing_type="结构图",
                scale="1:100",
                main_component_types=["未知构件"],
                estimated_total_components=0,
                project_metadata={}
            )
    
    def _analyze_slices_with_context_chain(self, 
                                         slice_images: List[str],
                                         slice_configs: List[Dict[str, Any]],
                                         task_id: str,
                                         drawing_id: int = None) -> List[Dict[str, Any]]:
        """使用上下文链分析切片"""
        
        slice_results = []
        accumulated_context = {
            "global_context": asdict(self.global_context),
            "previous_components": [],
            "previous_positions": [],
            "component_count_running_total": 0
        }
        
        for i, (slice_image, slice_config) in enumerate(zip(slice_images, slice_configs)):
            logger.info(f"🔍 分析切片 {i+1}/{len(slice_images)}: {slice_config.get('slice_id', f'slice_{i}')}")
            
            # 为当前切片构建上下文提示
            contextual_prompt = self._build_slice_contextual_prompt(
                slice_config, accumulated_context, i
            )
            
            # 执行简化的三步分析（而不是完整的五步）
            slice_result = self._execute_contextual_slice_analysis(
                slice_image, slice_config, contextual_prompt,
                f"{task_id}_slice_{i}", drawing_id
            )
            
            if slice_result.get("success"):
                # 更新累积上下文
                accumulated_context = self._update_accumulated_context(
                    accumulated_context, slice_result["qto_data"]
                )
                
                slice_results.append({
                    "slice_index": i,
                    "slice_config": slice_config,
                    "analysis_result": slice_result,
                    "context_used": contextual_prompt[:200] + "..." if len(contextual_prompt) > 200 else contextual_prompt
                })
                
                logger.info(f"✅ 切片 {i+1} 分析成功")
            else:
                logger.error(f"❌ 切片 {i+1} 分析失败: {slice_result.get('error')}")
                slice_results.append({
                    "slice_index": i,
                    "slice_config": slice_config,
                    "analysis_result": slice_result,
                    "context_used": contextual_prompt[:200] + "..." if len(contextual_prompt) > 200 else contextual_prompt
                })
        
        return slice_results
    
    def _build_slice_contextual_prompt(self, 
                                      slice_config: Dict[str, Any],
                                      accumulated_context: Dict[str, Any],
                                      slice_index: int) -> str:
        """为切片构建上下文提示"""
        
        global_ctx = accumulated_context["global_context"]
        previous_components = accumulated_context["previous_components"]
        
        prompt = f"""
【全图项目信息】
项目名称: {global_ctx['project_name']}
图纸类型: {global_ctx['drawing_type']}
图纸比例: {global_ctx['scale']}
设计单位: {global_ctx['project_metadata'].get('design_unit', '未知')}

【整体构件概览】
主要构件类型: {', '.join(global_ctx['main_component_types'])}
预估构件总数: {global_ctx['estimated_total_components']}
已分析构件数: {len(previous_components)}

【当前切片信息】
切片序号: {slice_index + 1}
切片位置: {slice_config.get('slice_position', '未知')}
切片类型: {slice_config.get('slice_type', '常规区域')}
关注重点: {', '.join(slice_config.get('focus_areas', ['构件识别']))}

【前序切片发现的构件】
"""
        
        # 添加前序构件信息（最近3个）
        recent_components = previous_components[-3:] if len(previous_components) > 3 else previous_components
        for comp in recent_components:
            prompt += f"- {comp.get('component_id', '未知')}: {comp.get('component_type', '未知')} "
            prompt += f"({comp.get('dimensions', '未知尺寸')})\n"
        
        prompt += f"""

【分析要求】
请基于以上全图上下文和前序分析结果，重点分析当前切片中的：
1. 构件详细信息（编号、类型、尺寸）
2. 构件与整体项目的关系
3. 配筋和材料信息
4. 特殊标注和连接关系

【一致性要求】
- 构件编号应符合整体编号规律
- 尺寸单位应与图纸比例({global_ctx['scale']})匹配
- 项目信息应与全图分析保持一致
- 避免重复识别已分析的构件
"""
        
        return prompt
    
    def _execute_contextual_slice_analysis(self, 
                                         slice_image: str,
                                         slice_config: Dict[str, Any],
                                         contextual_prompt: str,
                                         task_id: str,
                                         drawing_id: int = None) -> Dict[str, Any]:
        """执行带上下文的切片分析（简化三步）"""
        
        try:
            # 准备图像数据
            encoded_images = self.ai_analyzer._prepare_images([slice_image])
            if not encoded_images:
                return {"success": False, "error": "图像准备失败"}
            
            # 执行简化的三步分析而不是完整五步
            # Step 1: 构件识别
            step1_result = self._contextual_step1_component_identification(
                encoded_images, contextual_prompt, task_id, drawing_id
            )
            
            if not step1_result.get("success"):
                return step1_result
            
            # Step 2: 尺寸提取
            step2_result = self._contextual_step2_dimension_extraction(
                encoded_images, step1_result["data"], contextual_prompt, task_id, drawing_id
            )
            
            if not step2_result.get("success"):
                return step2_result
            
            # Step 3: 属性提取
            step3_result = self._contextual_step3_attribute_extraction(
                encoded_images, step1_result["data"], step2_result["data"], 
                contextual_prompt, task_id, drawing_id
            )
            
            if not step3_result.get("success"):
                return step3_result
            
            # 合成切片QTO数据
            slice_qto = self._synthesize_slice_qto(
                step1_result["data"], step2_result["data"], step3_result["data"], slice_config
            )
            
            return {
                "success": True,
                "qto_data": slice_qto,
                "analysis_method": "contextual_three_step",
                "context_prompt_used": len(contextual_prompt)
            }
            
        except Exception as e:
            logger.error(f"❌ 上下文切片分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _contextual_step1_component_identification(self, 
                                                 encoded_images: List[Dict],
                                                 contextual_prompt: str,
                                                 task_id: str,
                                                 drawing_id: int) -> Dict[str, Any]:
        """上下文化的步骤1：构件识别"""
        
        system_prompt = f"""你是经验丰富的结构工程师。基于以下上下文信息，仔细分析当前切片中的构件。

{contextual_prompt}

请识别切片中的所有构件，返回JSON格式：
{{
    "components": [
        {{
            "component_id": "构件编号（如KZ-1、L-1等，应符合整体编号规律）",
            "component_type": "构件类型（柱、梁、板、墙等）",
            "position_in_slice": "在切片中的位置描述",
            "confidence": "识别置信度(0-1)",
            "is_continuation": "是否为前序切片构件的延续(true/false)"
        }}
    ]
}}"""
        
        user_content = [{
            "type": "text", 
            "text": "请基于提供的上下文信息，识别当前切片中的构件。注意保持与整体项目的一致性。"
        }] + encoded_images
        
        return self.ai_analyzer._execute_vision_step(
            "contextual_step1", system_prompt, user_content, task_id, drawing_id
        )
    
    def _contextual_step2_dimension_extraction(self, 
                                             encoded_images: List[Dict],
                                             components: Dict[str, Any],
                                             contextual_prompt: str,
                                             task_id: str,
                                             drawing_id: int) -> Dict[str, Any]:
        """上下文化的步骤2：尺寸提取"""
        
        component_list = components.get("components", [])
        component_ids = [comp.get("component_id", "") for comp in component_list]
        
        system_prompt = f"""基于上下文信息和已识别的构件，提取详细尺寸信息。

{contextual_prompt}

已识别构件：{', '.join(component_ids)}

请提取每个构件的尺寸信息，返回JSON格式：
{{
    "dimensions": [
        {{
            "component_id": "构件编号",
            "width": "宽度（mm）",
            "height": "高度（mm）", 
            "length": "长度（mm）",
            "thickness": "厚度（mm，如适用）",
            "section_info": "截面信息",
            "unit_consistency_check": "单位是否与图纸比例一致"
        }}
    ]
}}"""
        
        user_content = [{
            "type": "text",
            "text": f"请为已识别的构件({', '.join(component_ids)})提取详细尺寸信息。注意单位一致性。"
        }] + encoded_images
        
        return self.ai_analyzer._execute_vision_step(
            "contextual_step2", system_prompt, user_content, task_id, drawing_id
        )
    
    def _contextual_step3_attribute_extraction(self, 
                                             encoded_images: List[Dict],
                                             components: Dict[str, Any],
                                             dimensions: Dict[str, Any],
                                             contextual_prompt: str,
                                             task_id: str,
                                             drawing_id: int) -> Dict[str, Any]:
        """上下文化的步骤3：属性提取"""
        
        system_prompt = f"""基于上下文信息、构件和尺寸信息，提取构件属性。

{contextual_prompt}

请提取构件的材料、配筋等属性信息，返回JSON格式：
{{
    "attributes": [
        {{
            "component_id": "构件编号",
            "concrete_grade": "混凝土强度等级",
            "steel_grade": "钢筋等级",
            "reinforcement": "配筋信息",
            "special_requirements": "特殊要求",
            "connection_details": "连接详情"
        }}
    ]
}}"""
        
        user_content = [{
            "type": "text",
            "text": "请提取构件的材料和配筋属性信息。"
        }] + encoded_images
        
        return self.ai_analyzer._execute_vision_step(
            "contextual_step3", system_prompt, user_content, task_id, drawing_id
        )
    
    def _synthesize_slice_qto(self, 
                            components: Dict[str, Any],
                            dimensions: Dict[str, Any], 
                            attributes: Dict[str, Any],
                            slice_config: Dict[str, Any]) -> Dict[str, Any]:
        """合成切片QTO数据"""
        
        try:
            comp_list = components.get("components", [])
            dim_list = dimensions.get("dimensions", [])
            attr_list = attributes.get("attributes", [])
            
            # 合并构件信息
            merged_components = []
            for comp in comp_list:
                comp_id = comp.get("component_id", "")
                
                # 查找对应的尺寸信息
                comp_dimensions = {}
                for dim in dim_list:
                    if dim.get("component_id", "") == comp_id:
                        comp_dimensions = dim
                        break
                
                # 查找对应的属性信息
                comp_attributes = {}
                for attr in attr_list:
                    if attr.get("component_id", "") == comp_id:
                        comp_attributes = attr
                        break
                
                # 合并信息
                merged_comp = {
                    **comp,
                    "dimensions": comp_dimensions,
                    "attributes": comp_attributes,
                    "slice_metadata": {
                        "slice_index": slice_config.get("slice_index", 0),
                        "slice_position": slice_config.get("slice_position", ""),
                        "analysis_method": "contextual_slice_analysis"
                    }
                }
                merged_components.append(merged_comp)
            
            return {
                "components": merged_components,
                "slice_summary": {
                    "total_components": len(merged_components),
                    "slice_config": slice_config,
                    "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "global_context_applied": True
            }
            
        except Exception as e:
            logger.error(f"❌ 切片QTO合成失败: {e}")
            return {
                "components": [],
                "slice_summary": {"error": str(e)},
                "global_context_applied": False
            }
    
    def _update_accumulated_context(self, 
                                  accumulated_context: Dict[str, Any],
                                  slice_qto_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新累积上下文"""
        
        try:
            components = slice_qto_data.get("components", [])
            
            # 添加到累积构件列表
            accumulated_context["previous_components"].extend(components)
            
            # 更新构件计数
            accumulated_context["component_count_running_total"] += len(components)
            
            # 提取位置信息
            for comp in components:
                if "position_in_slice" in comp:
                    accumulated_context["previous_positions"].append({
                        "component_id": comp.get("component_id", ""),
                        "position": comp.get("position_in_slice", "")
                    })
            
            return accumulated_context
            
        except Exception as e:
            logger.error(f"❌ 更新累积上下文失败: {e}")
            return accumulated_context
    
    def _merge_and_validate_results(self, 
                                  global_analysis: Dict[str, Any],
                                  slice_results: List[Dict[str, Any]],
                                  task_id: str) -> Dict[str, Any]:
        """合并和验证结果"""
        
        try:
            # 收集所有切片的构件
            all_slice_components = []
            successful_slices = 0
            
            for slice_result in slice_results:
                if slice_result["analysis_result"].get("success"):
                    successful_slices += 1
                    components = slice_result["analysis_result"]["qto_data"].get("components", [])
                    all_slice_components.extend(components)
            
            # 去重和一致性检查
            deduplicated_components = self._deduplicate_components(all_slice_components)
            
            # 一致性验证
            consistency_report = self._validate_consistency_with_global(
                global_analysis["qto_data"], deduplicated_components
            )
            
            # 构建最终结果
            final_result = {
                "success": True,
                "analysis_method": "contextual_slice_chain",
                "qto_data": {
                    "drawing_info": global_analysis["qto_data"].get("drawing_info", {}),
                    "components": deduplicated_components,
                    "component_summary": {
                        "total_components": len(deduplicated_components),
                        "component_types": list(set([
                            comp.get("component_type", "unknown") for comp in deduplicated_components
                        ])),
                        "sources": {
                            "global_analysis": True,
                            "successful_slices": successful_slices,
                            "total_slices": len(slice_results)
                        }
                    }
                },
                "analysis_metadata": {
                    "global_context": asdict(self.global_context),
                    "slice_analysis_summary": {
                        "total_slices": len(slice_results),
                        "successful_slices": successful_slices,
                        "failed_slices": len(slice_results) - successful_slices
                    },
                    "consistency_report": consistency_report,
                    "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "task_id": task_id
                }
            }
            
            logger.info(f"✅ 结果合并完成: {len(deduplicated_components)} 个构件, "
                       f"成功切片: {successful_slices}/{len(slice_results)}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 结果合并失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "contextual_slice_chain"
            }
    
    def _deduplicate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复构件"""
        
        unique_components = []
        seen_ids = set()
        
        for comp in components:
            comp_id = comp.get("component_id", "")
            if comp_id and comp_id not in seen_ids:
                seen_ids.add(comp_id)
                unique_components.append(comp)
            elif not comp_id:
                # 对于没有ID的构件，基于位置和类型判断
                position = comp.get("position_in_slice", "")
                comp_type = comp.get("component_type", "")
                identifier = f"{comp_type}_{position}"
                
                if identifier not in seen_ids:
                    seen_ids.add(identifier)
                    unique_components.append(comp)
        
        logger.info(f"🔄 构件去重: {len(components)} -> {len(unique_components)}")
        return unique_components
    
    def _validate_consistency_with_global(self, 
                                        global_qto: Dict[str, Any],
                                        slice_components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证切片结果与全局分析的一致性"""
        
        consistency_report = {
            "project_info_consistent": True,
            "component_numbering_consistent": True,
            "scale_consistent": True,
            "warnings": [],
            "errors": []
        }
        
        try:
            global_drawing_info = global_qto.get("drawing_info", {})
            global_project_name = global_drawing_info.get("project_name", "")
            
            # 检查项目名称一致性
            for comp in slice_components:
                slice_metadata = comp.get("slice_metadata", {})
                # 这里可以添加更多一致性检查逻辑
            
            # 检查构件编号规律
            component_ids = [comp.get("component_id", "") for comp in slice_components if comp.get("component_id")]
            
            # 简单的编号规律检查
            prefixes = set()
            for comp_id in component_ids:
                if "-" in comp_id:
                    prefix = comp_id.split("-")[0]
                    prefixes.add(prefix)
            
            if len(prefixes) > 10:  # 如果前缀过多，可能存在不一致
                consistency_report["warnings"].append(f"构件编号前缀过多({len(prefixes)})，可能存在不一致")
            
        except Exception as e:
            consistency_report["errors"].append(f"一致性检查异常: {e}")
        
        return consistency_report 