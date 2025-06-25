#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片Vision分析器
负责基于OCR结果的增强Vision分析
"""

import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GridSliceVisionAnalyzer:
    """网格切片Vision分析器"""
    
    def __init__(self, core_analyzer):
        """初始化Vision分析器"""
        self.core_analyzer = core_analyzer
        
        # 初始化AI分析器
        self.ai_analyzer = core_analyzer.ai_analyzer

    def analyze_slices_with_enhanced_vision(self, drawing_info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """增强Vision分析（基于OCR结果）"""
        try:
            logger.info(f"🔍 开始增强Vision分析，切片数量: {len(self.core_analyzer.enhanced_slices)}")
            
            if not self.ai_analyzer:
                logger.warning("⚠️ AI分析器不可用，跳过Vision分析")
                return {"success": False, "error": "AI分析器不可用"}
            
            vision_results = []
            processed_count = 0
            
            for slice_info in self.core_analyzer.enhanced_slices:
                try:
                    # 生成增强Vision提示词（基于OCR结果）
                    enhanced_prompt = self._generate_enhanced_vision_prompt(slice_info, drawing_info)
                    slice_info.enhanced_prompt = enhanced_prompt
                    
                    # 执行Vision分析
                    vision_result = self._analyze_single_slice_with_vision(
                        slice_info, enhanced_prompt, f"{task_id}_slice_{slice_info.row}_{slice_info.col}"
                    )
                    
                    if vision_result["success"]:
                        # 解析Vision结果
                        slice_components = self._parse_vision_components(vision_result, slice_info)
                        
                        # 存储到核心分析器
                        slice_key = f"{slice_info.row}_{slice_info.col}"
                        self.core_analyzer.slice_components[slice_key] = slice_components
                        
                        vision_results.append({
                            "slice_key": slice_key,
                            "components": slice_components,
                            "analysis_success": True
                        })
                    else:
                        logger.warning(f"⚠️ 切片 {slice_info.row}_{slice_info.col} Vision分析失败")
                        vision_results.append({
                            "slice_key": f"{slice_info.row}_{slice_info.col}",
                            "components": [],
                            "analysis_success": False,
                            "error": vision_result.get("error", "未知错误")
                        })
                    
                    processed_count += 1
                    
                    if processed_count % 5 == 0:
                        logger.info(f"📊 Vision分析进度: {processed_count}/{len(self.core_analyzer.enhanced_slices)}")
                        
                except Exception as slice_error:
                    logger.error(f"❌ 切片 {slice_info.row}_{slice_info.col} Vision分析异常: {slice_error}")
                    continue
            
            logger.info(f"✅ Vision分析完成: 处理 {processed_count} 个切片")
            
            return {
                "success": True,
                "vision_results": vision_results,
                "processed_count": processed_count,
                "total_components": sum(len(r.get("components", [])) for r in vision_results)
            }
            
        except Exception as e:
            logger.error(f"❌ 增强Vision分析失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _generate_enhanced_vision_prompt(self, slice_info, drawing_info: Dict[str, Any]) -> str:
        """生成增强Vision提示词（基于OCR结果）"""
        try:
            # 收集切片中的OCR文本
            ocr_texts = []
            if slice_info.ocr_results:
                for ocr_item in slice_info.ocr_results:
                    if ocr_item.text and ocr_item.text.strip():
                        ocr_texts.append(ocr_item.text.strip())
            
            # 构建增强提示词
            prompt_parts = [
                "# 建筑结构图纸构件识别任务",
                "",
                "## 任务目标",
                "基于OCR识别到的文本信息，分析图像中的建筑结构构件，提取构件编号、类型、尺寸等信息。",
                "",
                "## OCR识别文本信息",
                f"本区域识别到的文本: {', '.join(ocr_texts) if ocr_texts else '无明显文本'}",
                "",
                "## 分析要求",
                "1. 识别构件编号（如：B101, KZ01, GL201等）",
                "2. 识别构件类型（梁、柱、板、墙、基础等）", 
                "3. 识别尺寸信息（长×宽×高或截面尺寸）",
                "4. 识别材料等级（如：C30, HRB400等）",
                "5. 识别轴线信息（如：A-B, 1-2等）",
                "",
                "## 输出格式",
                "请以JSON格式输出识别结果：",
                "{",
                "  \"components\": [",
                "    {",
                "      \"component_id\": \"构件编号\",",
                "      \"component_type\": \"构件类型\",", 
                "      \"dimensions\": \"尺寸信息\",",
                "      \"material\": \"材料信息\",",
                "      \"position\": \"位置描述\",",
                "      \"confidence\": 0.9",
                "    }",
                "  ]",
                "}"
            ]
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"❌ 生成Vision提示词失败: {e}")
            return "请分析图像中的建筑结构构件信息。"

    def _analyze_single_slice_with_vision(self, slice_info, prompt: str, vision_task_id: str) -> Dict[str, Any]:
        """对单个切片执行Vision分析"""
        try:
            if not self.ai_analyzer:
                return {"success": False, "error": "AI分析器不可用"}
            
            # 检查Vision缓存
            cache_key = f"{slice_info.row}_{slice_info.col}_{hash(prompt)}"
            if cache_key in self.core_analyzer._vision_cache:
                logger.info(f"📋 使用缓存的Vision结果: {slice_info.row}_{slice_info.col}")
                return {
                    "success": True,
                    "analysis_result": self.core_analyzer._vision_cache[cache_key],
                    "cached": True
                }
            
            # 执行Vision分析
            analysis_result = self.ai_analyzer.analyze_image_with_text(
                image_path=slice_info.slice_path,
                prompt=prompt,
                task_id=vision_task_id
            )
            
            if analysis_result.get("success"):
                # 缓存结果
                self.core_analyzer._vision_cache[cache_key] = analysis_result.get("analysis", {})
                
                return {
                    "success": True,
                    "analysis_result": analysis_result.get("analysis", {}),
                    "cached": False
                }
            else:
                return {
                    "success": False,
                    "error": analysis_result.get("error", "Vision分析失败")
                }
                
        except Exception as e:
            logger.error(f"❌ 单个切片Vision分析失败: {e}")
            return {"success": False, "error": str(e)}

    def _parse_vision_components(self, vision_data: Dict[str, Any], slice_info) -> List[Dict[str, Any]]:
        """解析Vision分析结果中的构件信息"""
        try:
            components = []
            
            analysis_result = vision_data.get("analysis_result", {})
            if isinstance(analysis_result, str):
                # 尝试解析JSON字符串
                import json
                try:
                    analysis_result = json.loads(analysis_result)
                except:
                    logger.warning(f"⚠️ 无法解析Vision分析结果为JSON")
                    return []
            
            # 提取构件信息
            vision_components = analysis_result.get("components", [])
            if not isinstance(vision_components, list):
                logger.warning(f"⚠️ Vision结果格式异常，components不是列表")
                return []
            
            for comp_data in vision_components:
                try:
                    component = {
                        "component_id": comp_data.get("component_id", "").strip(),
                        "component_type": comp_data.get("component_type", "").strip(),
                        "dimensions": comp_data.get("dimensions", "").strip(),
                        "material": comp_data.get("material", "").strip(),
                        "position": comp_data.get("position", "").strip(),
                        "confidence": float(comp_data.get("confidence", 0.8)),
                        "source_slice": f"{slice_info.row}_{slice_info.col}",
                        "slice_coordinates": {
                            "x_offset": slice_info.x_offset,
                            "y_offset": slice_info.y_offset,
                            "width": slice_info.width,
                            "height": slice_info.height
                        },
                        "analysis_method": "enhanced_vision"
                    }
                    
                    # 验证构件信息完整性
                    if component["component_id"] or component["component_type"]:
                        components.append(component)
                        
                except Exception as comp_error:
                    logger.warning(f"⚠️ 解析单个构件信息失败: {comp_error}")
                    continue
            
            logger.info(f"📊 切片 {slice_info.row}_{slice_info.col} 解析出 {len(components)} 个构件")
            return components
            
        except Exception as e:
            logger.error(f"❌ 解析Vision构件信息失败: {e}")
            return []

    def get_vision_cache_status(self) -> Dict[str, Any]:
        """获取Vision缓存状态"""
        return {
            "cache_size": len(self.core_analyzer._vision_cache),
            "cache_keys": list(self.core_analyzer._vision_cache.keys())
        }

    def clear_vision_cache(self):
        """清理Vision缓存"""
        self.core_analyzer._vision_cache.clear()
        logger.info("🧹 Vision缓存已清理")

    def cleanup(self):
        """清理资源"""
        self.clear_vision_cache() 