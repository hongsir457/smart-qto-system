#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片分析系统
基于四步式架构：切片索引 → GPT分析 → 语义合并 → 坐标还原
"""

import os
import json
import logging
import uuid
import time
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class SliceInfo:
    """切片信息"""
    filename: str
    row: int
    col: int
    x_offset: int
    y_offset: int
    source_page: int
    width: int
    height: int
    slice_path: str

@dataclass
class ComponentInfo:
    """构件信息"""
    id: str
    type: str
    size: str
    material: str
    location: str
    source_block: str
    confidence: float = 1.0
    local_bbox: Optional[Dict[str, int]] = None
    global_coordinates: Optional[Dict[str, int]] = None

class GridSliceAnalyzer:
    """网格切片分析器"""
    
    def __init__(self, slice_size: int = 1024, overlap: int = 128):
        """
        初始化网格切片分析器
        
        Args:
            slice_size: 切片大小（像素）
            overlap: 重叠区域大小（像素）
        """
        self.slice_size = slice_size
        self.overlap = overlap
        self.ai_analyzer = None
        
        try:
            from app.services.ai_analyzer import AIAnalyzerService
            self.ai_analyzer = AIAnalyzerService()
        except Exception as e:
            logger.warning(f"⚠️ AI分析器初始化失败: {e}")
        
        # 存储分析结果
        self.slices: List[SliceInfo] = []
        self.slice_components: Dict[str, List[ComponentInfo]] = {}
        self.merged_components: List[ComponentInfo] = []
        
    def analyze_drawing_with_grid_slicing(self, 
                                        image_path: str,
                                        drawing_info: Dict[str, Any],
                                        task_id: str,
                                        output_dir: str = "temp_slices") -> Dict[str, Any]:
        """
        执行完整的四步网格切片分析
        
        Args:
            image_path: 图纸路径
            drawing_info: 图纸基本信息（比例、图号、页码等）
            task_id: 任务ID
            output_dir: 切片输出目录
            
        Returns:
            分析结果
        """
        logger.info(f"🚀 开始四步网格切片分析: {image_path}")
        
        try:
            # Step 1: 图纸切片（记录位置索引）
            logger.info("📐 Step 1: 图纸网格切片")
            slice_result = self._slice_drawing_to_grid(image_path, output_dir, drawing_info)
            if not slice_result["success"]:
                return slice_result
            
            # Step 2: GPT分析每张切片
            logger.info("🧠 Step 2: GPT分析每张切片")
            analysis_result = self._analyze_all_slices(drawing_info, task_id)
            if not analysis_result["success"]:
                return analysis_result
            
            # Step 3: 汇总构件表（合并语义）
            logger.info("📚 Step 3: 智能合并构件语义")
            merge_result = self._merge_component_semantics()
            if not merge_result["success"]:
                return merge_result
            
            # Step 4: 可视化还原（可选）
            logger.info("📎 Step 4: 坐标还原与可视化")
            restore_result = self._restore_global_coordinates(image_path)
            
            # 构建最终结果
            final_result = {
                "success": True,
                "analysis_method": "grid_slice_analysis",
                "qto_data": {
                    "drawing_info": drawing_info,
                    "components": [asdict(comp) for comp in self.merged_components],
                    "component_summary": {
                        "total_components": len(self.merged_components),
                        "component_types": list(set([comp.type for comp in self.merged_components])),
                        "analysis_coverage": {
                            "total_slices": len(self.slices),
                            "analyzed_slices": len([s for s in self.slice_components.values() if s]),
                            "coverage_ratio": len([s for s in self.slice_components.values() if s]) / len(self.slices) if self.slices else 0
                        }
                    }
                },
                "slice_metadata": {
                    "slice_info": [asdict(slice_info) for slice_info in self.slices],
                    "slice_size": self.slice_size,
                    "overlap": self.overlap,
                    "merge_statistics": merge_result.get("statistics", {}),
                    "coordinate_restoration": restore_result.get("success", False)
                },
                "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "task_id": task_id
            }
            
            logger.info(f"✅ 四步网格切片分析完成: {len(self.merged_components)} 个构件")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 网格切片分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_method": "grid_slice_analysis"
            }
    
    def _slice_drawing_to_grid(self, 
                             image_path: str, 
                             output_dir: str,
                             drawing_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1: 将图纸按网格切片，记录位置索引
        """
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 读取原图
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            height, width = image.shape[:2]
            logger.info(f"📏 原图尺寸: {width}x{height}")
            
            # 计算网格参数
            step_size = self.slice_size - self.overlap
            rows = math.ceil((height - self.overlap) / step_size)
            cols = math.ceil((width - self.overlap) / step_size)
            
            logger.info(f"📐 网格切片参数: {rows}行 x {cols}列, 切片大小: {self.slice_size}, 重叠: {self.overlap}")
            
            self.slices = []
            slice_count = 0
            
            for row in range(rows):
                for col in range(cols):
                    # 计算切片位置
                    x_offset = col * step_size
                    y_offset = row * step_size
                    
                    # 确保不超出图像边界
                    x_end = min(x_offset + self.slice_size, width)
                    y_end = min(y_offset + self.slice_size, height)
                    
                    # 如果切片太小，跳过
                    actual_width = x_end - x_offset
                    actual_height = y_end - y_offset
                    if actual_width < 256 or actual_height < 256:
                        continue
                    
                    # 提取切片
                    slice_image = image[y_offset:y_end, x_offset:x_end]
                    
                    # 保存切片
                    slice_filename = f"slice_{row}_{col}.png"
                    slice_path = os.path.join(output_dir, slice_filename)
                    cv2.imwrite(slice_path, slice_image)
                    
                    # 记录切片信息
                    slice_info = SliceInfo(
                        filename=slice_filename,
                        row=row,
                        col=col,
                        x_offset=x_offset,
                        y_offset=y_offset,
                        source_page=drawing_info.get("page_number", 1),
                        width=actual_width,
                        height=actual_height,
                        slice_path=slice_path
                    )
                    
                    self.slices.append(slice_info)
                    slice_count += 1
                    
                    logger.debug(f"📐 切片 {slice_count}: {slice_filename} "
                               f"位置({x_offset},{y_offset}) 尺寸{actual_width}x{actual_height}")
            
            logger.info(f"✅ 网格切片完成: 共生成 {len(self.slices)} 个切片")
            
            return {
                "success": True,
                "slice_count": len(self.slices),
                "grid_size": f"{rows}x{cols}",
                "output_directory": output_dir
            }
            
        except Exception as e:
            logger.error(f"❌ 网格切片失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_all_slices(self, 
                          drawing_info: Dict[str, Any],
                          task_id: str) -> Dict[str, Any]:
        """
        Step 2: 用GPT分析每张切片
        """
        if not self.ai_analyzer or not self.ai_analyzer.is_available():
            return {
                "success": False,
                "error": "AI分析器不可用"
            }
        
        try:
            analyzed_count = 0
            failed_count = 0
            
            for slice_info in self.slices:
                logger.info(f"🧠 分析切片 {slice_info.row}_{slice_info.col}: {slice_info.filename}")
                
                # 构建切片分析提示
                slice_prompt = self._build_slice_analysis_prompt(slice_info, drawing_info)
                
                # 执行切片分析
                slice_result = self._analyze_single_slice(
                    slice_info, slice_prompt, f"{task_id}_slice_{slice_info.row}_{slice_info.col}"
                )
                
                if slice_result["success"]:
                    # 解析构件信息
                    components = self._parse_slice_components(slice_result["data"], slice_info)
                    self.slice_components[f"{slice_info.row}_{slice_info.col}"] = components
                    analyzed_count += 1
                    
                    logger.info(f"✅ 切片 {slice_info.row}_{slice_info.col} 分析成功: {len(components)} 个构件")
                else:
                    logger.error(f"❌ 切片 {slice_info.row}_{slice_info.col} 分析失败: {slice_result.get('error')}")
                    self.slice_components[f"{slice_info.row}_{slice_info.col}"] = []
                    failed_count += 1
            
            success_rate = analyzed_count / len(self.slices) if self.slices else 0
            
            logger.info(f"📊 切片分析完成: 成功 {analyzed_count}/{len(self.slices)} ({success_rate:.1%})")
            
            return {
                "success": True,
                "analyzed_slices": analyzed_count,
                "failed_slices": failed_count,
                "success_rate": success_rate
            }
            
        except Exception as e:
            logger.error(f"❌ 切片分析过程失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_slice_analysis_prompt(self, 
                                   slice_info: SliceInfo,
                                   drawing_info: Dict[str, Any]) -> str:
        """构建切片分析提示词"""
        
        prompt = f"""📄 当前图块：{slice_info.filename}（第{slice_info.row}行第{slice_info.col}列）
图纸比例：{drawing_info.get('scale', '1:100')}，图号 {drawing_info.get('drawing_number', 'S03')}，页码{slice_info.source_page}

切片位置信息：
- 行列索引：第{slice_info.row}行第{slice_info.col}列
- 原图偏移：({slice_info.x_offset}, {slice_info.y_offset})
- 切片尺寸：{slice_info.width}x{slice_info.height}

请识别所有构件编号、类型、尺寸、材料、以及位置（如轴线A-C/1-3，或相对坐标）

返回JSON格式：
[
  {{
    "id": "构件编号（如B101、KZ-1等）",
    "type": "构件类型（梁、柱、板、墙等）",
    "size": "尺寸规格（如300x600）",
    "material": "材料等级（如C30、HRB400）",
    "location": "位置描述（轴线或相对坐标）",
    "local_bbox": {{"x": "局部x坐标", "y": "局部y坐标", "width": "宽度", "height": "高度"}},
    "confidence": "识别置信度(0-1)"
  }}
]

注意事项：
1. 只识别当前切片中完整或主要部分的构件
2. 位置描述要尽可能具体和准确
3. 如果构件跨越切片边界，在location中标注"跨界"
4. 对于模糊或不确定的构件，降低confidence值"""

        return prompt
    
    def _analyze_single_slice(self, 
                            slice_info: SliceInfo,
                            prompt: str,
                            slice_task_id: str) -> Dict[str, Any]:
        """分析单个切片"""
        
        try:
            # 准备图像数据
            encoded_images = self.ai_analyzer._prepare_images([slice_info.slice_path])
            if not encoded_images:
                return {"success": False, "error": "图像准备失败"}
            
            # 构建系统提示
            system_prompt = """你是专业的结构工程师，具有丰富的建筑图纸识别经验。
请仔细分析提供的图纸切片，准确识别其中的构件信息。

要求：
1. 严格按照JSON格式返回结果
2. 只识别能够清晰看到的构件
3. 对于模糊或不确定的内容，诚实标注低置信度
4. 位置描述要具体，便于后续合并分析"""
            
            # 构建用户内容
            user_content = [
                {"type": "text", "text": prompt}
            ] + encoded_images
            
            # 执行分析
            result = self.ai_analyzer._execute_vision_step(
                f"slice_analysis", system_prompt, user_content, 
                slice_task_id, None
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 单个切片分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_slice_components(self, 
                              analysis_data: Dict[str, Any],
                              slice_info: SliceInfo) -> List[ComponentInfo]:
        """解析切片分析结果中的构件信息"""
        
        components = []
        
        try:
            # 尝试直接解析components字段
            if "components" in analysis_data:
                component_list = analysis_data["components"]
            elif isinstance(analysis_data, list):
                component_list = analysis_data
            else:
                logger.warning(f"⚠️ 切片 {slice_info.row}_{slice_info.col} 分析结果格式异常")
                return components
            
            for comp_data in component_list:
                if isinstance(comp_data, dict):
                    component = ComponentInfo(
                        id=comp_data.get("id", ""),
                        type=comp_data.get("type", "未知"),
                        size=comp_data.get("size", ""),
                        material=comp_data.get("material", ""),
                        location=comp_data.get("location", ""),
                        source_block=f"{slice_info.row}_{slice_info.col}",
                        confidence=float(comp_data.get("confidence", 0.8)),
                        local_bbox=comp_data.get("local_bbox", {})
                    )
                    
                    if component.id:  # 只添加有ID的构件
                        components.append(component)
            
        except Exception as e:
            logger.error(f"❌ 解析切片构件信息失败: {e}")
        
        return components
    
    def _merge_component_semantics(self) -> Dict[str, Any]:
        """
        Step 3: 汇总构件表（合并语义）
        实现智能合并逻辑
        """
        try:
            logger.info("📚 开始智能合并构件语义...")
            
            # 收集所有构件
            all_components = []
            for slice_key, components in self.slice_components.items():
                all_components.extend(components)
            
            logger.info(f"📊 收集到 {len(all_components)} 个原始构件")
            
            # 初始化合并统计
            merge_stats = {
                "original_count": len(all_components),
                "exact_duplicates": 0,
                "similar_merges": 0,
                "cross_slice_merges": 0,
                "conflicts_resolved": 0
            }
            
            self.merged_components = []
            processed_indices = set()
            
            for i, component in enumerate(all_components):
                if i in processed_indices:
                    continue
                
                # 查找相似或重复的构件
                similar_components = [component]
                similar_indices = [i]
                
                for j, other_component in enumerate(all_components[i+1:], i+1):
                    if j in processed_indices:
                        continue
                    
                    merge_type = self._should_merge_components(component, other_component)
                    if merge_type:
                        similar_components.append(other_component)
                        similar_indices.append(j)
                        
                        # 更新统计
                        if merge_type == "exact":
                            merge_stats["exact_duplicates"] += 1
                        elif merge_type == "similar":
                            merge_stats["similar_merges"] += 1
                        elif merge_type == "cross_slice":
                            merge_stats["cross_slice_merges"] += 1
                
                # 合并相似构件
                if len(similar_components) > 1:
                    merged_component = self._merge_similar_components(similar_components)
                    logger.debug(f"🔀 合并构件 {merged_component.id}: {len(similar_components)} 个来源")
                else:
                    merged_component = component
                
                self.merged_components.append(merged_component)
                processed_indices.update(similar_indices)
            
            merge_stats["final_count"] = len(self.merged_components)
            merge_stats["merge_ratio"] = 1 - (len(self.merged_components) / len(all_components)) if all_components else 0
            
            logger.info(f"✅ 构件语义合并完成: {len(all_components)} → {len(self.merged_components)} "
                       f"(合并率: {merge_stats['merge_ratio']:.1%})")
            
            return {
                "success": True,
                "statistics": merge_stats
            }
            
        except Exception as e:
            logger.error(f"❌ 构件语义合并失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _should_merge_components(self, 
                               comp1: ComponentInfo, 
                               comp2: ComponentInfo) -> Optional[str]:
        """判断两个构件是否应该合并，返回合并类型"""
        
        # 1. 完全相同的构件编号
        if comp1.id == comp2.id and comp1.id:
            return "exact"
        
        # 2. 相似编号（可能是OCR错误）
        if self._is_similar_id(comp1.id, comp2.id):
            # 检查类型和尺寸是否匹配
            if comp1.type == comp2.type and self._is_similar_size(comp1.size, comp2.size):
                return "similar"
        
        # 3. 跨切片的同一构件（位置连续）
        if (comp1.type == comp2.type and 
            self._is_similar_size(comp1.size, comp2.size) and
            self._is_adjacent_location(comp1, comp2)):
            return "cross_slice"
        
        return None
    
    def _is_similar_id(self, id1: str, id2: str) -> bool:
        """判断两个ID是否相似（处理OCR错误）"""
        if not id1 or not id2:
            return False
        
        # 计算编辑距离
        import difflib
        similarity = difflib.SequenceMatcher(None, id1.lower(), id2.lower()).ratio()
        return similarity > 0.8
    
    def _is_similar_size(self, size1: str, size2: str) -> bool:
        """判断两个尺寸是否相似"""
        if not size1 or not size2:
            return True  # 如果其中一个尺寸为空，认为兼容
        
        # 简单的字符串比较
        return size1.replace(" ", "").lower() == size2.replace(" ", "").lower()
    
    def _is_adjacent_location(self, comp1: ComponentInfo, comp2: ComponentInfo) -> bool:
        """判断两个构件是否在相邻位置（跨切片）"""
        
        try:
            # 解析source_block
            row1, col1 = map(int, comp1.source_block.split("_"))
            row2, col2 = map(int, comp2.source_block.split("_"))
            
            # 检查是否相邻
            row_diff = abs(row1 - row2)
            col_diff = abs(col1 - col2)
            
            # 相邻切片：行或列相差1，且另一个相差0或1
            return (row_diff <= 1 and col_diff <= 1) and (row_diff + col_diff > 0)
            
        except:
            return False
    
    def _merge_similar_components(self, components: List[ComponentInfo]) -> ComponentInfo:
        """合并相似的构件"""
        
        # 以置信度最高的构件为基准
        base_component = max(components, key=lambda c: c.confidence)
        
        # 合并source_block信息
        source_blocks = list(set([comp.source_block for comp in components]))
        
        # 合并位置信息
        locations = [comp.location for comp in components if comp.location]
        merged_location = " | ".join(set(locations)) if locations else base_component.location
        
        # 创建合并后的构件
        merged_component = ComponentInfo(
            id=base_component.id,
            type=base_component.type,
            size=base_component.size,
            material=base_component.material,
            location=merged_location,
            source_block=" + ".join(source_blocks),
            confidence=sum([comp.confidence for comp in components]) / len(components),
            local_bbox=base_component.local_bbox
        )
        
        return merged_component
    
    def _restore_global_coordinates(self, original_image_path: str) -> Dict[str, Any]:
        """
        Step 4: 坐标还原与可视化
        将切片中的构件坐标映射回原图坐标系
        """
        try:
            logger.info("📎 开始坐标还原与可视化...")
            
            restored_count = 0
            
            for component in self.merged_components:
                if component.local_bbox and component.source_block:
                    # 查找对应的切片信息
                    slice_info = self._find_slice_info(component.source_block)
                    if slice_info:
                        # 计算全局坐标
                        local_bbox = component.local_bbox
                        global_bbox = {
                            "x": slice_info.x_offset + local_bbox.get("x", 0),
                            "y": slice_info.y_offset + local_bbox.get("y", 0),
                            "width": local_bbox.get("width", 0),
                            "height": local_bbox.get("height", 0)
                        }
                        
                        component.global_coordinates = global_bbox
                        restored_count += 1
            
            logger.info(f"✅ 坐标还原完成: {restored_count}/{len(self.merged_components)} 个构件")
            
            # 可选：生成可视化图像
            visualization_result = self._create_visualization(original_image_path)
            
            return {
                "success": True,
                "restored_count": restored_count,
                "total_components": len(self.merged_components),
                "visualization": visualization_result
            }
            
        except Exception as e:
            logger.error(f"❌ 坐标还原失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _find_slice_info(self, source_block: str) -> Optional[SliceInfo]:
        """查找切片信息"""
        try:
            # 处理合并后的source_block（可能包含多个切片）
            first_block = source_block.split(" + ")[0]
            row, col = map(int, first_block.split("_"))
            
            for slice_info in self.slices:
                if slice_info.row == row and slice_info.col == col:
                    return slice_info
            
        except:
            pass
        
        return None
    
    def _create_visualization(self, original_image_path: str) -> Dict[str, Any]:
        """创建可视化图像（可选）"""
        try:
            # 读取原图
            image = cv2.imread(original_image_path)
            if image is None:
                return {"success": False, "error": "无法读取原图"}
            
            # 在图像上绘制构件边界框
            for component in self.merged_components:
                if component.global_coordinates:
                    bbox = component.global_coordinates
                    
                    # 绘制边界框
                    cv2.rectangle(
                        image,
                        (int(bbox["x"]), int(bbox["y"])),
                        (int(bbox["x"] + bbox["width"]), int(bbox["y"] + bbox["height"])),
                        (0, 255, 0),  # 绿色
                        2
                    )
                    
                    # 添加构件ID标签
                    cv2.putText(
                        image,
                        component.id,
                        (int(bbox["x"]), int(bbox["y"] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1
                    )
            
            # 保存可视化结果
            vis_path = original_image_path.replace(".", "_components.")
            cv2.imwrite(vis_path, image)
            
            logger.info(f"📊 可视化图像保存: {vis_path}")
            
            return {
                "success": True,
                "visualization_path": vis_path,
                "annotated_components": len([c for c in self.merged_components if c.global_coordinates])
            }
            
        except Exception as e:
            logger.error(f"❌ 创建可视化失败: {e}")
            return {
                "success": False,
                "error": str(e)
            } 