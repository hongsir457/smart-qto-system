# -*- coding: utf-8 -*-
"""
切片OCR管理器：负责OCR加载、缓存、复用、解析、增强等
"""
import os
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from .enhanced_slice_models import OCRTextItem, EnhancedSliceInfo

logger = logging.getLogger(__name__)

class SliceOCRManager:
    def __init__(self, analyzer):
        self.analyzer = analyzer  # 回调主流程
        self.ocr_cache = analyzer.ocr_cache
        self.component_patterns = analyzer._default_component_patterns()

    def can_reuse_slice_ocr(self, slice_info: EnhancedSliceInfo) -> bool:
        try:
            if hasattr(self.analyzer, 'shared_slice_results') and self.analyzer.shared_slice_results:
                for original_path, slice_result in self.analyzer.shared_slice_results.items():
                    slice_infos = slice_result.get('slice_infos', [])
                    for info in slice_infos:
                        if (info.get('row') == slice_info.row and \
                            info.get('col') == slice_info.col and
                            info.get('ocr_results')):
                            return True
            if hasattr(self.analyzer, '_slice_ocr_cache'):
                slice_key = f"{slice_info.row}_{slice_info.col}_{slice_info.slice_path}"
                return slice_key in self.analyzer._slice_ocr_cache
            return False
        except Exception as e:
            logger.debug(f"⚠️ 检查OCR复用失败: {e}")
            return False

    def load_cached_ocr_results(self, slice_info: EnhancedSliceInfo) -> List[OCRTextItem]:
        try:
            if hasattr(self.analyzer, 'shared_slice_results') and self.analyzer.shared_slice_results:
                for original_path, slice_result in self.analyzer.shared_slice_results.items():
                    slice_infos = slice_result.get('slice_infos', [])
                    for info in slice_infos:
                        if (info.get('row') == slice_info.row and \
                            info.get('col') == slice_info.col):
                            ocr_data = info.get('ocr_results', [])
                            if ocr_data:
                                return self.convert_to_ocr_text_items(ocr_data)
            if hasattr(self.analyzer, '_slice_ocr_cache'):
                slice_key = f"{slice_info.row}_{slice_info.col}_{slice_info.slice_path}"
                cached_data = self.analyzer._slice_ocr_cache.get(slice_key)
                if cached_data:
                    return self.convert_to_ocr_text_items(cached_data)
            return []
        except Exception as e:
            logger.debug(f"⚠️ 加载缓存OCR结果失败: {e}")
            return []

    def convert_to_ocr_text_items(self, ocr_data: List[Dict]) -> List[OCRTextItem]:
        ocr_items = []
        for item in ocr_data:
            try:
                if isinstance(item, dict):
                    ocr_item = OCRTextItem(
                        text=item.get('text', ''),
                        position=item.get('position', []),
                        confidence=item.get('confidence', 0.0),
                        category=item.get('category', 'unknown'),
                        bbox=item.get('bbox', {})
                    )
                    ocr_items.append(ocr_item)
                elif hasattr(item, 'text'):
                    ocr_items.append(item)
            except Exception as e:
                logger.debug(f"⚠️ 转换OCR项失败: {e}")
                continue
        return ocr_items

    def cache_slice_ocr_results(self, slice_info: EnhancedSliceInfo):
        try:
            if not hasattr(self.analyzer, '_slice_ocr_cache'):
                self.analyzer._slice_ocr_cache = {}
            slice_key = f"{slice_info.row}_{slice_info.col}_{slice_info.slice_path}"
            ocr_data = []
            for ocr_item in slice_info.ocr_results or []:
                ocr_data.append({
                    'text': ocr_item.text,
                    'position': ocr_item.position,
                    'confidence': ocr_item.confidence,
                    'category': ocr_item.category,
                    'bbox': ocr_item.bbox
                })
            self.analyzer._slice_ocr_cache[slice_key] = ocr_data
        except Exception as e:
            logger.debug(f"⚠️ 缓存OCR结果失败: {e}")

    def save_global_ocr_cache(self):
        try:
            if not hasattr(self.analyzer, '_global_ocr_cache'):
                self.analyzer._global_ocr_cache = {}
            for slice_info in self.analyzer.enhanced_slices:
                if slice_info.ocr_results:
                    slice_key = f"{slice_info.row}_{slice_info.col}"
                    ocr_data = []
                    for ocr_item in slice_info.ocr_results:
                        ocr_data.append({
                            'text': ocr_item.text,
                            'position': ocr_item.position,
                            'confidence': ocr_item.confidence,
                            'category': ocr_item.category,
                            'bbox': ocr_item.bbox
                        })
                    self.analyzer._global_ocr_cache[slice_key] = ocr_data
            logger.debug(f"💾 全局OCR缓存已保存: {len(self.analyzer._global_ocr_cache)} 个切片")
        except Exception as e:
            logger.debug(f"⚠️ 保存全局OCR缓存失败: {e}")

    def reuse_global_ocr_cache(self) -> Dict[str, Any]:
        try:
            total_text_items = 0
            reused_slices = 0
            for slice_info in self.analyzer.enhanced_slices:
                slice_key = f"{slice_info.row}_{slice_info.col}"
                if slice_key in self.analyzer._global_ocr_cache:
                    ocr_data = self.analyzer._global_ocr_cache[slice_key]
                    slice_info.ocr_results = self.convert_to_ocr_text_items(ocr_data)
                    total_text_items += len(slice_info.ocr_results)
                    reused_slices += 1
                    logger.debug(f"♻️ 切片 {slice_key} 复用全局缓存: {len(slice_info.ocr_results)} 个文本项")
                else:
                    slice_info.ocr_results = []
            logger.info(f"♻️ 全局OCR缓存复用完成: {reused_slices}/{len(self.analyzer.enhanced_slices)} 个切片, 共 {total_text_items} 个文本项")
            return {
                "success": True,
                "statistics": {
                    "processed_slices": 0,
                    "reused_slices": reused_slices,
                    "total_slices": len(self.analyzer.enhanced_slices),
                    "total_text_items": total_text_items,
                    "success_rate": reused_slices / len(self.analyzer.enhanced_slices) if self.analyzer.enhanced_slices else 0,
                    "reuse_rate": 1.0
                }
            }
        except Exception as e:
            logger.error(f"❌ 复用全局OCR缓存失败: {e}")
            return {"success": False, "error": str(e)}

    def parse_ocr_results(self, ocr_texts: List[Dict]) -> List[OCRTextItem]:
        ocr_items = []
        for item in ocr_texts:
            try:
                text = item.get("text", "").strip()
                confidence = item.get("confidence", 0.0)
                bbox_xyxy = item.get("bbox_xyxy", {})
                if bbox_xyxy:
                    x_min = bbox_xyxy.get("x_min", 0)
                    y_min = bbox_xyxy.get("y_min", 0)
                    x_max = bbox_xyxy.get("x_max", 0)
                    y_max = bbox_xyxy.get("y_max", 0)
                    position = [
                        [x_min, y_min],
                        [x_max, y_min],
                        [x_max, y_max],
                        [x_min, y_max]
                    ]
                else:
                    position = []
                if text and position:
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

    def enhance_slices_with_ocr(self, enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        try:
            enhanced_count = 0
            classification_stats = {
                "component_id": 0,
                "dimension": 0,
                "material": 0,
                "axis": 0,
                "unknown": 0
            }
            for slice_info in enhanced_slices:
                if not slice_info.ocr_results:
                    continue
                self.classify_ocr_texts(slice_info.ocr_results)
                slice_info.enhanced_prompt = self.generate_enhanced_prompt(slice_info)
                if slice_info.enhanced_prompt:
                    enhanced_count += 1
                for ocr_item in slice_info.ocr_results:
                    classification_stats[ocr_item.category] += 1
            logger.info(f"📊 OCR增强完成: {enhanced_count}/{len(enhanced_slices)} 个切片生成增强提示")
            return {
                "success": True,
                "statistics": {
                    "enhanced_slices": enhanced_count,
                    "total_slices": len(enhanced_slices),
                    "classification_stats": classification_stats
                }
            }
        except Exception as e:
            logger.error(f"❌ OCR增强失败: {e}")
            return {"success": False, "error": str(e)}

    def classify_ocr_texts(self, ocr_results: List[OCRTextItem]):
        for ocr_item in ocr_results:
            text = ocr_item.text.strip()
            for category, patterns in self.component_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, text, re.IGNORECASE):
                        ocr_item.category = category
                        break
                if ocr_item.category != "unknown":
                    break

    def generate_enhanced_prompt(self, slice_info: EnhancedSliceInfo) -> str:
        if not slice_info.ocr_results:
            return ""
        categorized_items = {}
        for ocr_item in slice_info.ocr_results:
            category = ocr_item.category
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(ocr_item)
        prompt_parts = []
        if hasattr(self.analyzer, 'global_drawing_overview') and self.analyzer.global_drawing_overview:
            overview = self.analyzer.global_drawing_overview
            prompt_parts.append("🌍 全图概览信息：")
            if overview.get('natural_language_summary'):
                prompt_parts.append("【全图分析摘要】")
                prompt_parts.append(overview['natural_language_summary'])
                prompt_parts.append("")
            else:
                drawing_info = overview.get('drawing_info', {})
                if drawing_info:
                    prompt_parts.append(f"- 图纸类型: {drawing_info.get('drawing_type', '未知')}")
                    prompt_parts.append(f"- 工程名称: {drawing_info.get('project_name', '未知')}")
                    prompt_parts.append(f"- 图纸比例: {drawing_info.get('scale', '未知')}")
                component_ids = overview.get('component_ids', [])
                if component_ids:
                    prompt_parts.append(f"- 全图构件编号: {', '.join(component_ids[:10])}{'...' if len(component_ids) > 10 else ''}")
                component_types = overview.get('component_types', [])
                if component_types:
                    prompt_parts.append(f"- 主要构件类型: {', '.join(component_types)}")
                material_grades = overview.get('material_grades', [])
                if material_grades:
                    prompt_parts.append(f"- 材料等级: {', '.join(material_grades)}")
                axis_lines = overview.get('axis_lines', [])
                if axis_lines:
                    prompt_parts.append(f"- 轴线编号: {', '.join(axis_lines[:8])}{'...' if len(axis_lines) > 8 else ''}")
                summary = overview.get('summary', {})
                if summary:
                    prompt_parts.append(f"- 复杂程度: {summary.get('complexity_level', '未知')}")
                prompt_parts.append("")
        tile_pos = f"第{slice_info.row}行第{slice_info.col}列"
        prompt_parts.append(f"📄 当前图像为结构图切片（{tile_pos}），尺寸 {slice_info.width}x{slice_info.height}")
        if categorized_items:
            prompt_parts.append("\n🔍 当前切片OCR识别的构件信息：")
            category_names = {
                "component_id": "构件编号",
                "dimension": "尺寸规格",
                "material": "材料等级",
                "axis": "轴线位置"
            }
            for category, items in categorized_items.items():
                if category == "unknown":
                    continue
                category_name = category_names.get(category, category)
                texts = [item.text for item in items]
                if texts:
                    max_items_per_category = 8
                    if len(texts) > max_items_per_category:
                        display_texts = texts[:max_items_per_category] + [f"...等{len(texts)}项"]
                        logger.debug(f"⚠️ 切片 {slice_info.row}_{slice_info.col} {category_name}项目过多，已截断: {len(texts)}项")
                    else:
                        display_texts = texts
                    prompt_parts.append(f"- {category_name}: {', '.join(display_texts)}")
        prompt_parts.append("\n👁️ Vision构件识别要求（重点：几何形状，非文本）：")
        prompt_parts.append("1. 🔍 OCR文本匹配：将OCR识别的构件编号与图像中的构件进行匹配")
        prompt_parts.append("2. 🌍 全图上下文：结合全图构件清单，理解当前切片的构件分布")
        prompt_parts.append("3. 📐 几何形状识别：识别梁（矩形）、柱（圆形/方形）、板（面状）、墙（线状）等")
        prompt_parts.append("4. 📏 尺寸测量：基于图纸比例计算构件的实际尺寸（长宽高厚）")
        prompt_parts.append("5. 🔗 连接关系：识别构件间的连接和支撑关系")
        prompt_parts.append("6. 📊 工程量数据：提供面积、体积等工程量计算所需的几何参数")
        prompt_parts.append("\n📋 返回JSON格式，重点包含：")
        prompt_parts.append("- 构件几何形状和精确尺寸（用于工程量计算）")
        prompt_parts.append("- 构件边界框和空间位置")
        prompt_parts.append("- 构件结构作用和连接关系")
        prompt_parts.append("- OCR文本与Vision构件的匹配关系")
        prompt_parts.append("注意：专注构件识别，不要重复OCR的文本识别工作")
        return "\n".join(prompt_parts) 