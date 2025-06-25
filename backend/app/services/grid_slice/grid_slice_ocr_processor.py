#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片OCR处理器
负责OCR结果的处理、缓存和复用逻辑
"""

import os
import json
import logging
import tempfile
import base64
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# 导入核心模块
from .grid_slice_analyzer_core import OCRTextItem, EnhancedSliceInfo
from app.utils.analysis_optimizations import ocr_cache_manager

logger = logging.getLogger(__name__)

class GridSliceOCRProcessor:
    """网格切片OCR处理器"""
    
    def __init__(self, core_analyzer):
        """初始化OCR处理器"""
        self.core_analyzer = core_analyzer
        self.ocr_cache = ocr_cache_manager
        
        # 初始化OCR引擎
        try:
            from app.services.ocr.paddle_ocr import PaddleOCRService
            self.ocr_engine = PaddleOCRService()
        except Exception as e:
            logger.warning(f"⚠️ OCR引擎初始化失败: {e}")
            self.ocr_engine = None

    def can_reuse_shared_slices(self, shared_slice_results: Dict[str, Any], image_path: str) -> bool:
        """检查是否可以复用共享切片结果"""
        # 基础验证逻辑
        required_keys = ['slice_infos', 'original_width', 'original_height']
        for key in required_keys:
            if key not in shared_slice_results:
                logger.error(f"❌ 共享切片结果缺少必需字段: {key}")
                return False
        
        slice_infos = shared_slice_results.get('slice_infos', [])
        if not slice_infos:
            logger.error("❌ 共享切片结果为空")
            return False
        
        # 验证切片数据完整性
        for i, slice_info in enumerate(slice_infos):
            if not hasattr(slice_info, 'base64_data') or not slice_info.base64_data:
                logger.error(f"❌ 切片 {i} 缺少base64数据")
                return False
        
        logger.info(f"✅ 共享切片验证通过，切片数量: {len(slice_infos)}")
        return True

    def reuse_shared_slices(self, shared_slice_results: Dict[str, Any], image_path: str, drawing_info: Dict[str, Any]) -> Dict[str, Any]:
        """复用共享切片结果"""
        try:
            slice_infos = shared_slice_results.get('slice_infos', [])
            original_width = shared_slice_results.get('original_width', 0)
            original_height = shared_slice_results.get('original_height', 0)
            
            logger.info(f"📐 开始复用共享切片: {len(slice_infos)}个切片")
            
            # 清空现有切片
            self.core_analyzer.enhanced_slices = []
            
            # 防重复坐标集合
            seen_coordinates = set()
            
            for i, slice_data in enumerate(slice_infos):
                # 创建临时切片文件
                try:
                    slice_image_data = base64.b64decode(slice_data.base64_data)
                    temp_slice_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    temp_slice_file.write(slice_image_data)
                    temp_slice_file.close()
                    
                    # 智能计算行列，避免重复标识
                    if original_width > 0 and original_height > 0:
                        # 估算网格大小（根据切片数量和图片尺寸）
                        total_slices = len(slice_infos)
                        estimated_rows = math.ceil(math.sqrt(total_slices * original_height / original_width))
                        estimated_cols = math.ceil(total_slices / estimated_rows)
                        
                        # 基于位置精确计算行列
                        if estimated_rows > 0 and estimated_cols > 0:
                            row_height = max(1, original_height // estimated_rows)
                            col_width = max(1, original_width // estimated_cols)
                            row = min(slice_data.y // row_height, estimated_rows - 1)
                            col = min(slice_data.x // col_width, estimated_cols - 1)
                        else:
                            # 备用方案：基于索引计算
                            estimated_cols = max(1, math.ceil(math.sqrt(len(slice_infos))))
                            row = i // estimated_cols
                            col = i % estimated_cols
                    else:
                        # 备用方案：基于索引计算
                        estimated_cols = max(1, math.ceil(math.sqrt(len(slice_infos))))
                        row = i // estimated_cols
                        col = i % estimated_cols
                    
                    # 防重复检查
                    coordinate_key = f"{row}_{col}"
                    if coordinate_key in seen_coordinates:
                        # 调整坐标避免重复
                        adjustment = 1
                        while f"{row + adjustment}_{col}" in seen_coordinates:
                            adjustment += 1
                        row = row + adjustment
                        coordinate_key = f"{row}_{col}"
                    
                    seen_coordinates.add(coordinate_key)
                    
                    enhanced_slice_info = EnhancedSliceInfo(
                        filename=f"reused_slice_{row}_{col}.png",
                        row=row,
                        col=col,
                        x_offset=slice_data.x,
                        y_offset=slice_data.y,
                        source_page=drawing_info.get("page_number", 1),
                        width=slice_data.width,
                        height=slice_data.height,
                        slice_path=temp_slice_file.name,
                        ocr_results=[],  # 稍后会填充
                        enhanced_prompt=""
                    )
                    
                    self.core_analyzer.enhanced_slices.append(enhanced_slice_info)
                    
                except Exception as e:
                    logger.error(f"❌ 处理切片 {i} 失败: {e}")
                    continue
            
            # 修复重复的切片ID
            self._fix_duplicate_slice_ids()
            
            logger.info(f"✅ 共享切片复用完成: {len(self.core_analyzer.enhanced_slices)}个有效切片")
            
            return {
                "success": True,
                "slice_count": len(self.core_analyzer.enhanced_slices),
                "original_image_info": {
                    "width": original_width,
                    "height": original_height,
                    "path": image_path
                },
                "slice_coordinate_map": self._build_slice_coordinate_map()
            }
            
        except Exception as e:
            logger.error(f"❌ 复用共享切片失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def load_shared_ocr_results(self, shared_slice_results: Dict[str, Any], image_path: str) -> Dict[str, Any]:
        """从共享切片结果中加载OCR数据"""
        try:
            # 检查是否存在缓存的OCR结果
            if hasattr(shared_slice_results, 'ocr_cache_key') and shared_slice_results.ocr_cache_key:
                cached_results = self.ocr_cache.get_cached_ocr_results(shared_slice_results.ocr_cache_key)
                if cached_results:
                    logger.info("📋 使用缓存的OCR结果")
                    return self._apply_cached_ocr_results(cached_results)
            
            # 如果没有缓存，则执行OCR处理
            logger.info("🔍 开始OCR处理...")
            return self._extract_ocr_from_slices_optimized()
            
        except Exception as e:
            logger.error(f"❌ 加载共享OCR结果失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _extract_ocr_from_slices_optimized(self) -> Dict[str, Any]:
        """从切片中提取OCR结果（优化版）"""
        try:
            ocr_texts = []
            processed_count = 0
            cache_hit_count = 0
            
            logger.info(f"🔍 开始OCR处理，切片数量: {len(self.core_analyzer.enhanced_slices)}")
            
            for slice_info in self.core_analyzer.enhanced_slices:
                # 检查OCR缓存
                if self._can_reuse_slice_ocr(slice_info):
                    cached_results = self._load_cached_ocr_results(slice_info)
                    slice_info.ocr_results = cached_results
                    cache_hit_count += 1
                else:
                    # 执行OCR识别
                    slice_ocr_results = self._perform_slice_ocr(slice_info)
                    slice_info.ocr_results = slice_ocr_results
                    # 缓存结果
                    self._cache_slice_ocr_results(slice_info)
                
                # 收集OCR文本
                if slice_info.ocr_results:
                    for ocr_item in slice_info.ocr_results:
                        ocr_texts.append(ocr_item.text)
                
                processed_count += 1
                
                if processed_count % 10 == 0:
                    logger.info(f"📊 OCR进度: {processed_count}/{len(self.core_analyzer.enhanced_slices)}, 缓存命中: {cache_hit_count}")
            
            logger.info(f"✅ OCR处理完成: 处理 {processed_count} 个切片, 缓存命中 {cache_hit_count} 个")
            
            # 提取全图OCR概览
            overview_result = self._extract_global_ocr_overview_optimized(ocr_texts)
            
            return {
                "success": True,
                "ocr_texts": ocr_texts,
                "slice_count": processed_count,
                "cache_hit_count": cache_hit_count,
                "global_overview": overview_result.get("global_overview", {})
            }
            
        except Exception as e:
            logger.error(f"❌ OCR提取失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _can_reuse_slice_ocr(self, slice_info: EnhancedSliceInfo) -> bool:
        """检查是否可以复用切片OCR结果"""
        try:
            # 基于切片文件路径和修改时间生成缓存键
            if not os.path.exists(slice_info.slice_path):
                return False
            
            file_stat = os.stat(slice_info.slice_path)
            cache_key = f"slice_ocr_{slice_info.filename}_{file_stat.st_size}_{int(file_stat.st_mtime)}"
            
            return self.ocr_cache.has_cached_results(cache_key)
        except Exception:
            return False

    def _load_cached_ocr_results(self, slice_info: EnhancedSliceInfo) -> List[OCRTextItem]:
        """加载缓存的OCR结果"""
        try:
            file_stat = os.stat(slice_info.slice_path)
            cache_key = f"slice_ocr_{slice_info.filename}_{file_stat.st_size}_{int(file_stat.st_mtime)}"
            
            cached_data = self.ocr_cache.get_cached_ocr_results(cache_key)
            if cached_data:
                return self._convert_to_ocr_text_items(cached_data)
            return []
        except Exception as e:
            logger.warning(f"⚠️ 加载缓存OCR结果失败: {e}")
            return []

    def _perform_slice_ocr(self, slice_info: EnhancedSliceInfo) -> List[OCRTextItem]:
        """对单个切片执行OCR识别"""
        try:
            if not self.ocr_engine:
                logger.warning("⚠️ OCR引擎不可用")
                return []
            
            # 执行OCR识别
            ocr_results = self.ocr_engine.extract_text_from_image(slice_info.slice_path)
            
            # 转换为OCRTextItem格式
            ocr_items = []
            for result in ocr_results:
                try:
                    # 解析OCR结果格式
                    if isinstance(result, dict):
                        text = result.get('text', '')
                        confidence = result.get('confidence', 0.0)
                        position = result.get('position', [])
                    else:
                        # 处理其他格式
                        text = str(result)
                        confidence = 0.8
                        position = []
                    
                    if text.strip():
                        ocr_item = OCRTextItem(
                            text=text.strip(),
                            position=position,
                            confidence=confidence,
                            category="unknown",
                            bbox=self._calculate_bbox_from_position(position) if position else None
                        )
                        ocr_items.append(ocr_item)
                        
                except Exception as item_error:
                    logger.warning(f"⚠️ 处理OCR结果项失败: {item_error}")
                    continue
            
            return ocr_items
            
        except Exception as e:
            logger.error(f"❌ 切片OCR识别失败: {e}")
            return []

    def _cache_slice_ocr_results(self, slice_info: EnhancedSliceInfo):
        """缓存切片OCR结果"""
        try:
            if not slice_info.ocr_results:
                return
            
            file_stat = os.stat(slice_info.slice_path)
            cache_key = f"slice_ocr_{slice_info.filename}_{file_stat.st_size}_{int(file_stat.st_mtime)}"
            
            # 将OCRTextItem转换为可序列化的格式
            serializable_results = []
            for ocr_item in slice_info.ocr_results:
                serializable_results.append({
                    'text': ocr_item.text,
                    'position': ocr_item.position,
                    'confidence': ocr_item.confidence,
                    'category': ocr_item.category,
                    'bbox': ocr_item.bbox
                })
            
            self.ocr_cache.cache_ocr_results(cache_key, serializable_results)
            
        except Exception as e:
            logger.warning(f"⚠️ 缓存OCR结果失败: {e}")

    def _convert_to_ocr_text_items(self, ocr_data: List[Dict]) -> List[OCRTextItem]:
        """将缓存数据转换为OCRTextItem对象"""
        ocr_items = []
        for item_data in ocr_data:
            try:
                ocr_item = OCRTextItem(
                    text=item_data.get('text', ''),
                    position=item_data.get('position', []),
                    confidence=item_data.get('confidence', 0.0),
                    category=item_data.get('category', 'unknown'),
                    bbox=item_data.get('bbox')
                )
                ocr_items.append(ocr_item)
            except Exception as e:
                logger.warning(f"⚠️ 转换OCR数据项失败: {e}")
                continue
        return ocr_items

    def _calculate_bbox_from_position(self, position: List[List[int]]) -> Dict[str, int]:
        """从位置坐标计算边界框"""
        try:
            if not position or len(position) < 4:
                return None
            
            x_coords = [point[0] for point in position]
            y_coords = [point[1] for point in position]
            
            return {
                'x': min(x_coords),
                'y': min(y_coords),
                'width': max(x_coords) - min(x_coords),
                'height': max(y_coords) - min(y_coords)
            }
        except Exception:
            return None

    def _extract_global_ocr_overview_optimized(self, ocr_texts: List[str]) -> Dict[str, Any]:
        """提取全图OCR概览（优化版）"""
        try:
            # 实现全图OCR概览提取逻辑
            return {
                "global_overview": {
                    "total_texts": len(ocr_texts),
                    "analysis_method": "slice_based_ocr"
                }
            }
        except Exception as e:
            logger.error(f"❌ 全图OCR概览提取失败: {e}")
            return {"global_overview": {}}

    def _apply_cached_ocr_results(self, cached_results: Dict[str, Any]) -> Dict[str, Any]:
        """应用缓存的OCR结果"""
        try:
            # 应用缓存的OCR结果到切片
            for slice_info in self.core_analyzer.enhanced_slices:
                slice_key = f"{slice_info.row}_{slice_info.col}"
                if slice_key in cached_results:
                    slice_info.ocr_results = self._convert_to_ocr_text_items(cached_results[slice_key])
            
            return {"success": True}
        except Exception as e:
            logger.error(f"❌ 应用缓存OCR结果失败: {e}")
            return {"success": False, "error": str(e)}

    def _build_slice_coordinate_map(self) -> Dict[str, Any]:
        """构建切片坐标映射"""
        coordinate_map = {}
        for slice_info in self.core_analyzer.enhanced_slices:
            slice_key = f"{slice_info.row}_{slice_info.col}"
            coordinate_map[slice_key] = {
                'x_offset': slice_info.x_offset,
                'y_offset': slice_info.y_offset,
                'width': slice_info.width,
                'height': slice_info.height
            }
        return coordinate_map

    def _fix_duplicate_slice_ids(self):
        """修复重复的切片ID"""
        seen_ids = set()
        for i, slice_info in enumerate(self.core_analyzer.enhanced_slices):
            original_id = f"{slice_info.row}_{slice_info.col}"
            if original_id in seen_ids:
                # 调整重复的ID
                adjustment = 1
                new_id = f"{slice_info.row + adjustment}_{slice_info.col}"
                while new_id in seen_ids:
                    adjustment += 1
                    new_id = f"{slice_info.row + adjustment}_{slice_info.col}"
                
                slice_info.row = slice_info.row + adjustment
                slice_info.filename = f"reused_slice_{slice_info.row}_{slice_info.col}.png"
                seen_ids.add(new_id)
            else:
                seen_ids.add(original_id)

    def cleanup(self):
        """清理资源"""
        # 清理临时OCR文件等
        pass 