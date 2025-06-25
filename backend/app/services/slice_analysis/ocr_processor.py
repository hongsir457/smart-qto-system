#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR处理器
从enhanced_grid_slice_analyzer.py中提取的OCR相关功能
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..enhanced_slice_models import OCRTextItem, EnhancedSliceInfo
from ..ocr_enhancement import OCREnhancer
from app.utils.analysis_optimizations import (
    OCRCacheManager, AnalysisLogger, AnalysisMetadata,
    ocr_cache_manager
)

logger = logging.getLogger(__name__)

class OCRProcessor:
    """OCR处理器 - 负责OCR识别、缓存和增强处理"""
    
    def __init__(self):
        self.ocr_cache = ocr_cache_manager
        self.ocr_enhancer = OCREnhancer(self._default_component_patterns())
        
        # 初始化OCR引擎
        self.ocr_engine = None
        try:
            from app.services.ocr.paddle_ocr import PaddleOCRService
            self.ocr_engine = PaddleOCRService()
        except Exception as e:
            logger.warning(f"⚠️ OCR引擎初始化失败: {e}")
    
    def extract_ocr_from_slices_optimized(self, enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        """从切片中提取OCR文本（优化版本，支持缓存复用）"""
        try:
            all_ocr_texts = []
            cached_count = 0
            processed_count = 0
            
            for slice_info in enhanced_slices:
                if self._can_reuse_slice_ocr(slice_info):
                    # 复用缓存的OCR结果
                    cached_ocr = self._load_cached_ocr_results(slice_info)
                    all_ocr_texts.extend(cached_ocr)
                    cached_count += 1
                    logger.info(f"✅ 复用切片 {slice_info.slice_id} 的缓存OCR结果")
                else:
                    # 执行新的OCR识别
                    if self.ocr_engine:
                        slice_ocr_result = self.ocr_engine.extract_text_from_image(slice_info.slice_path)
                        if slice_ocr_result.get("success"):
                            ocr_texts = self._parse_ocr_results(slice_ocr_result.get("ocr_results", []))
                            all_ocr_texts.extend(ocr_texts)
                            
                            # 缓存当前切片的OCR结果
                            slice_info.ocr_texts = ocr_texts
                            self._cache_slice_ocr_results(slice_info)
                            processed_count += 1
                            
                            logger.info(f"✅ 处理切片 {slice_info.slice_id}: {len(ocr_texts)} 个文本")
                        else:
                            logger.warning(f"⚠️ 切片 {slice_info.slice_id} OCR识别失败")
                    else:
                        logger.warning(f"⚠️ OCR引擎未初始化，跳过切片 {slice_info.slice_id}")
            
            logger.info(f"✅ OCR提取完成: 缓存复用 {cached_count} 个，新处理 {processed_count} 个，总文本 {len(all_ocr_texts)} 条")
            
            return {
                "success": True,
                "ocr_texts": all_ocr_texts,
                "cached_count": cached_count,
                "processed_count": processed_count,
                "total_texts": len(all_ocr_texts)
            }
            
        except Exception as e:
            logger.error(f"❌ OCR提取过程发生错误: {e}")
            return {"success": False, "error": str(e)}
    
    def enhance_slices_with_ocr(self, enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        """对切片进行OCR增强处理"""
        try:
            enhanced_count = 0
            
            for slice_info in enhanced_slices:
                if slice_info.ocr_texts:
                    # 分类OCR文本
                    classification = self._classify_ocr_texts(slice_info.ocr_texts)
                    slice_info.ocr_classification = classification
                    
                    # 生成增强提示
                    enhanced_prompt = self._generate_enhanced_prompt(slice_info)
                    slice_info.enhanced_prompt = enhanced_prompt
                    
                    enhanced_count += 1
                    logger.debug(f"✅ 切片 {slice_info.slice_id} OCR增强完成")
            
            logger.info(f"✅ OCR增强处理完成: {enhanced_count} 个切片")
            
            return {
                "success": True,
                "enhanced_count": enhanced_count,
                "enhanced_slices": enhanced_slices
            }
            
        except Exception as e:
            logger.error(f"❌ OCR增强处理失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _can_reuse_slice_ocr(self, slice_info: EnhancedSliceInfo) -> bool:
        """检查是否可以复用切片的OCR缓存"""
        try:
            cache_key = f"slice_ocr_{slice_info.slice_id}"
            
            # 检查内存缓存
            if hasattr(slice_info, 'ocr_texts') and slice_info.ocr_texts:
                return True
            
            # 检查Redis缓存
            if self.ocr_cache and self.ocr_cache.exists(cache_key):
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ 检查OCR缓存时出错: {e}")
            return False
    
    def _load_cached_ocr_results(self, slice_info: EnhancedSliceInfo) -> List[OCRTextItem]:
        """加载缓存的OCR结果"""
        try:
            # 优先使用内存缓存
            if hasattr(slice_info, 'ocr_texts') and slice_info.ocr_texts:
                return slice_info.ocr_texts
            
            # 从Redis缓存加载
            cache_key = f"slice_ocr_{slice_info.slice_id}"
            if self.ocr_cache and self.ocr_cache.exists(cache_key):
                cached_data = self.ocr_cache.get(cache_key)
                if cached_data:
                    return self._convert_to_ocr_text_items(cached_data)
            
            return []
            
        except Exception as e:
            logger.warning(f"⚠️ 加载OCR缓存失败: {e}")
            return []
    
    def _convert_to_ocr_text_items(self, ocr_data: List[Dict]) -> List[OCRTextItem]:
        """将缓存数据转换为OCRTextItem对象"""
        try:
            ocr_items = []
            for item in ocr_data:
                if isinstance(item, dict) and 'text' in item:
                    ocr_item = OCRTextItem(
                        text=item['text'],
                        bbox=item.get('bbox', {}),
                        confidence=item.get('confidence', 0.0),
                        slice_id=item.get('slice_id', ''),
                        ocr_type=item.get('ocr_type', 'unknown')
                    )
                    ocr_items.append(ocr_item)
            return ocr_items
        except Exception as e:
            logger.warning(f"⚠️ 转换OCR数据失败: {e}")
            return []
    
    def _cache_slice_ocr_results(self, slice_info: EnhancedSliceInfo):
        """缓存切片的OCR结果"""
        try:
            if not slice_info.ocr_texts:
                return
            
            cache_key = f"slice_ocr_{slice_info.slice_id}"
            cache_data = []
            
            for ocr_item in slice_info.ocr_texts:
                cache_data.append({
                    'text': ocr_item.text,
                    'bbox': ocr_item.bbox,
                    'confidence': ocr_item.confidence,
                    'slice_id': ocr_item.slice_id,
                    'ocr_type': ocr_item.ocr_type
                })
            
            if self.ocr_cache:
                self.ocr_cache.set(cache_key, cache_data, expire=7200)  # 2小时过期
                logger.debug(f"✅ 缓存切片 {slice_info.slice_id} 的OCR结果")
                
        except Exception as e:
            logger.warning(f"⚠️ 缓存OCR结果失败: {e}")
    
    def _parse_ocr_results(self, ocr_texts: List[Dict]) -> List[OCRTextItem]:
        """解析OCR识别结果"""
        try:
            parsed_texts = []
            
            for i, item in enumerate(ocr_texts):
                if isinstance(item, dict):
                    text = item.get('text', '').strip()
                    if not text:
                        continue
                    
                    # 计算边界框
                    bbox = {}
                    if 'position' in item and item['position']:
                        bbox = self._calculate_bbox_from_position(item['position'])
                    
                    ocr_item = OCRTextItem(
                        text=text,
                        bbox=bbox,
                        confidence=item.get('confidence', 0.0),
                        slice_id='',
                        ocr_type='paddle_ocr'
                    )
                    parsed_texts.append(ocr_item)
            
            return parsed_texts
            
        except Exception as e:
            logger.error(f"❌ 解析OCR结果时出错: {e}")
            return []
    
    def _calculate_bbox_from_position(self, position: List[List[int]]) -> Dict[str, int]:
        """从位置坐标计算边界框"""
        try:
            if not position or len(position) < 4:
                return {}
            
            x_coords = [point[0] for point in position]
            y_coords = [point[1] for point in position]
            
            return {
                "x": min(x_coords),
                "y": min(y_coords),
                "width": max(x_coords) - min(x_coords),
                "height": max(y_coords) - min(y_coords)
            }
        except Exception as e:
            logger.warning(f"⚠️ 计算边界框失败: {e}")
            return {}
    
    def _classify_ocr_texts(self, ocr_results: List[OCRTextItem]) -> Dict[str, Any]:
        """分类OCR文本结果"""
        classification = {
            "component_ids": [],
            "dimensions": [],
            "annotations": [],
            "technical_specs": [],
            "other_texts": []
        }
        
        for ocr_item in ocr_results:
            text = ocr_item.text.strip()
            
            # 构件编号识别
            if any(pattern in text.upper() for pattern in ['KZ', 'L', 'B', 'Q', 'W']):
                classification["component_ids"].append(text)
            # 尺寸标注识别
            elif any(char in text for char in ['×', 'x', 'X', 'mm', 'cm', 'm']):
                classification["dimensions"].append(text)
            # 技术规格
            elif any(pattern in text.upper() for pattern in ['HRB', 'HPB', 'C30', 'C25', 'C35']):
                classification["technical_specs"].append(text)
            # 其他文本
            else:
                classification["other_texts"].append(text)
        
        return classification
    
    def _generate_enhanced_prompt(self, slice_info: EnhancedSliceInfo) -> str:
        """生成OCR增强提示"""
        if not slice_info.ocr_texts:
            return ""
        
        classification = getattr(slice_info, 'ocr_classification', {})
        
        prompt_parts = ["## OCR识别增强提示"]
        
        if classification.get("component_ids"):
            prompt_parts.append("### 识别到的构件编号:")
            for comp_id in classification["component_ids"]:
                prompt_parts.append(f"- {comp_id}")
        
        if classification.get("dimensions"):
            prompt_parts.append("### 识别到的尺寸标注:")
            for dim in classification["dimensions"]:
                prompt_parts.append(f"- {dim}")
        
        if classification.get("technical_specs"):
            prompt_parts.append("### 识别到的技术规格:")
            for spec in classification["technical_specs"]:
                prompt_parts.append(f"- {spec}")
        
        prompt_parts.append("### 分析要求:")
        prompt_parts.append("1. 重点关注上述OCR识别的关键信息")
        prompt_parts.append("2. 验证构件编号和尺寸的对应关系")
        prompt_parts.append("3. 确保技术规格的准确性")
        
        return "\n".join(prompt_parts)
    
    def _default_component_patterns(self):
        """默认构件模式"""
        return [
            "KZ", "L", "B", "Q", "W", "S", "T",  # 基本构件类型
            "柱", "梁", "板", "墙", "楼梯", "基础"   # 中文构件类型
        ] 