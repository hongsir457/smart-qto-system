#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR处理器模块 - 处理OCR相关的所有逻辑
"""

import os
import json
import logging
import time
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from ..enhanced_slice_models import OCRTextItem, EnhancedSliceInfo


class OCRHandler:
    """OCR处理器 - 负责OCR提取、缓存、分类等"""
    
    def __init__(self):
        """初始化OCR处理器"""
        self.component_patterns = self._default_component_patterns()
        
    def extract_ocr_from_slices_optimized(self, analyzer_self, enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        """优化的OCR提取方法，集成缓存管理和坐标转换"""
        try:
            from app.utils.analysis_optimizations import AnalysisLogger
            
            start_time = time.time()
            total_ocr_items = 0
            cached_slices = 0
            new_ocr_slices = 0
            
            AnalysisLogger.log_step("ocr_extraction_optimized", "开始优化OCR提取")
            
            for slice_info in enhanced_slices:
                try:
                    # 使用优化的OCR缓存管理器
                    cache_result = analyzer_self.ocr_cache.get_cached_ocr(
                        slice_info.slice_path, 
                        slice_info.filename
                    )
                    
                    if cache_result:
                        slice_info.ocr_results = cache_result
                        cached_slices += 1
                        AnalysisLogger.log_step("ocr_cache_hit", f"复用缓存: {slice_info.filename}")
                    else:
                        # 执行新的OCR分析
                        if not os.path.exists(slice_info.slice_path):
                            AnalysisLogger.log_step("ocr_skip", f"文件不存在: {slice_info.slice_path}")
                            continue
                            
                        # 调用PaddleOCR进行文本提取
                        ocr_texts = analyzer_self.ocr_engine.extract_text_from_image(slice_info.slice_path)
                        slice_info.ocr_results = self.parse_ocr_results(ocr_texts)
                        
                        # 缓存结果
                        analyzer_self.ocr_cache.cache_ocr_result(
                            slice_info.slice_path, 
                            slice_info.filename, 
                            slice_info.ocr_results
                        )
                        new_ocr_slices += 1
                        AnalysisLogger.log_step("ocr_new", f"新分析: {slice_info.filename}")
                    
                    total_ocr_items += len(slice_info.ocr_results) if slice_info.ocr_results else 0
                    
                except Exception as e:
                    AnalysisLogger.log_step("ocr_error", f"OCR失败: {slice_info.filename} - {e}")
                    slice_info.ocr_results = []
                    continue
            
            processing_time = time.time() - start_time
            
            # 统计信息
            statistics = {
                "total_slices": len(enhanced_slices),
                "cached_slices": cached_slices,
                "new_ocr_slices": new_ocr_slices,
                "total_ocr_items": total_ocr_items,
                "cache_hit_rate": cached_slices / len(enhanced_slices) if enhanced_slices else 0,
                "processing_time": processing_time
            }
            
            AnalysisLogger.log_step("ocr_extraction_completed", 
                                  f"OCR提取完成: {statistics}")
            
            logger.info(f"🔍 优化OCR提取完成: 总计{total_ocr_items}个文本项，"
                       f"缓存命中率{statistics['cache_hit_rate']:.1%}，耗时{processing_time:.2f}s")
            
            return {
                "success": True,
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"❌ 优化OCR提取失败: {e}")
            return {"success": False, "error": str(e)}

    def extract_global_ocr_overview_optimized(self, analyzer_self, enhanced_slices: List[EnhancedSliceInfo], 
                                             drawing_info: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """优化的全图OCR概览分析，使用统一的GPT响应解析器"""
        try:
            from app.utils.analysis_optimizations import GPTResponseParser, AnalysisLogger
            from app.services.ocr_result_corrector import OCRResultCorrector
            import json
            start_time = time.time()
            AnalysisLogger.log_step("global_ocr_overview", "开始全图OCR概览分析")

            # 汇总所有OCR文本区域（含坐标）
            text_regions = []
            for slice_info in enhanced_slices:
                if slice_info.ocr_results:
                    for item in slice_info.ocr_results:
                        text_regions.append({
                            "text": item.text,
                            "bbox": getattr(item, "bbox", None) or getattr(item, "position", None)
                        })

            if not text_regions:
                return {"success": False, "error": "没有OCR文本可分析"}

            # 用OCRResultCorrector拼接纯文本（排序、合并、聚类）
            try:
                corrector = OCRResultCorrector()
                ocr_plain_text = corrector.build_plain_text_from_regions(text_regions)
            except Exception as e:
                logger.warning(f"⚠️ OCRResultCorrector不可用，降级为简单拼接: {e}")
                ocr_plain_text = '\n'.join([r["text"] for r in text_regions])

            # 日志输出全图纯文本概览
            lines = ocr_plain_text.splitlines()
            logger.info(f"📋 全图文本概览（前5行）: {' | '.join(lines[:5])}")
            logger.info(f"📋 全图文本概览（后5行）: {' | '.join(lines[-5:])}")

            # 构建分析提示词
            analysis_prompt = self.build_global_overview_prompt(ocr_plain_text, drawing_info)

            # 调用AI分析
            if not analyzer_self.ai_analyzer:
                return {"success": False, "error": "AI分析器未初始化"}

            parser = GPTResponseParser()
            response = analyzer_self.ai_analyzer.analyze_with_context(
                prompt=analysis_prompt,
                context_type="global_overview",
                task_id=task_id
            )

            if not response.get("success"):
                return {"success": False, "error": response.get("error", "AI分析失败")}

            parsed_result = parser.parse_response(
                response.get("analysis", ""),
                expected_format="json",
                error_enabled=True
            )

            if not parsed_result.get("success"):
                return {"success": False, "error": "响应解析失败"}

            overview_data = parsed_result.get("data", {})
            processing_time = time.time() - start_time
            AnalysisLogger.log_step("global_overview_completed", f"全图概览完成，耗时{processing_time:.2f}s")

            return {
                "success": True,
                "overview": overview_data,
                "ocr_text_count": len(lines),
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"❌ 全图OCR概览分析失败: {e}")
            return {"success": False, "error": str(e)}

    def build_global_overview_prompt(self, ocr_plain_text: str, drawing_info: Dict[str, Any]) -> str:
        """为全图OCR概览构建Prompt（只用纯文本）"""
        truncation_note = "\n...(文本过长，已截断)" if len(ocr_plain_text) > 4000 else ""
        drawing_name = drawing_info.get('drawing_name', '未知')
        drawing_type = drawing_info.get('drawing_type', '建筑图纸')
        
        prompt = f"""
你是一位专业的建筑工程量计算专家。请分析以下从建筑图纸中提取的OCR文本（已按顺序排序、相邻合并），并提供结构化的全图概览信息。

图纸信息：
- 文件名：{drawing_name}
- 图纸类型：{drawing_type}

OCR提取的纯文本内容：
{ocr_plain_text[:4000]}{truncation_note}

请按以下JSON格式返回分析结果：
{{
    "drawing_info": {{
        "project_name": "工程名称",
        "drawing_type": "图纸类型",
        "scale": "图纸比例",
        "drawing_number": "图纸编号"
    }},
    "component_ids": ["构件编号列表"],
    "component_types": ["构件类型列表"],
    "material_grades": ["材料等级列表"],
    "axis_lines": ["轴线标识列表"],
    "summary": {{
        "total_components": 0,
        "main_structure_type": "主要结构类型",
        "drawing_complexity": "图纸复杂程度"
    }}
}}

要求：
1. 准确识别图纸中的构件编号（如：KL1、Z1、B1等）
2. 识别构件类型（如：框架梁、柱、板等）
3. 提取材料等级信息（如：C30、HRB400等）
4. 识别轴线标识（如：A、B、C、1、2、3等）
5. 返回标准JSON格式，不要包含其他说明文字
"""
        return prompt

    def parse_ocr_results(self, ocr_texts: List[Dict]) -> List[OCRTextItem]:
        """解析OCR结果为标准格式"""
        ocr_items = []
        
        for item in ocr_texts:
            try:
                text = item.get("text", "").strip()
                confidence = item.get("confidence", 0.0)
                
                # 从PaddleOCR的bbox_xyxy格式转换为position格式
                bbox_xyxy = item.get("bbox_xyxy", {})
                if bbox_xyxy:
                    # 转换bbox为四个角点坐标
                    x_min = bbox_xyxy.get("x_min", 0)
                    y_min = bbox_xyxy.get("y_min", 0)
                    x_max = bbox_xyxy.get("x_max", 0)
                    y_max = bbox_xyxy.get("y_max", 0)
                    
                    position = [
                        [x_min, y_min],  # 左上
                        [x_max, y_min],  # 右上
                        [x_max, y_max],  # 右下
                        [x_min, y_max]   # 左下
                    ]
                else:
                    position = []
                
                if text and position:
                    # 计算标准化边界框
                    bbox = self.calculate_bbox_from_position(position)
                    
                    ocr_item = OCRTextItem(
                        text=text,
                        position=position,
                        confidence=confidence,
                        category="unknown",
                        bbox=bbox
                    )
                    
                    ocr_items.append(ocr_item)
                    
            except Exception as e:
                logger.warning(f"⚠️ 解析OCR项失败: {e}")
                continue
        
        return ocr_items

    def calculate_bbox_from_position(self, position: List[List[int]]) -> Dict[str, int]:
        """从位置点计算边界框"""
        if len(position) < 4:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        xs = [p[0] for p in position]
        ys = [p[1] for p in position]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        return {
            "x": x_min,
            "y": y_min,
            "width": x_max - x_min,
            "height": y_max - y_min
        }

    def _default_component_patterns(self):
        """默认构件模式"""
        return {
            'component_id': [r'^[A-Z]{1,2}\d{2,4}$', r'^[A-Z]{1,2}-\d{1,3}$', r'^\d{1,3}[A-Z]{1,2}$'],
            'dimension': [r'^\d{2,4}[xX×]\d{2,4}$', r'^\d{2,4}[xX×]\d{2,4}[xX×]\d{2,4}$', r'^[bBhH]?\d{2,4}$'],
            'material': [r'^C\d{2}$', r'^HRB\d{3}$', r'^MU\d{1,2}$', r'^Q\d{3}$'],
            'axis': [r'^[A-Z]-[A-Z]$', r'^\d+-\d+$', r'^轴线\s*[A-Z0-9\-/]+$', r'^[A-Z]\d*/[A-Z]\d*$']
        }
