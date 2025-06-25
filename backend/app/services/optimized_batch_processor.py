#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的批次处理器
集成OCR缓存管理、分析器实例复用、统一日志记录等优化功能
"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from app.utils.analysis_optimizations import (
    AnalyzerInstanceManager, AnalysisLogger, AnalysisMetadata, 
    ocr_cache_manager, GPTResponseParser
)
from app.core.config import AnalysisSettings

logger = logging.getLogger(__name__)

class OptimizedBatchProcessor:
    """优化的批次处理器"""
    
    def __init__(self):
        """初始化优化批次处理器"""
        self.analyzer_manager = AnalyzerInstanceManager()
        self.ocr_cache = ocr_cache_manager
        self.global_ocr_cache = {}
        self.ocr_cache_initialized = False
    
    def process_slices_in_batches_optimized(self, 
                                          vision_image_data: List[Dict],
                                          task_id: str,
                                          drawing_id: int,
                                          shared_slice_results: Dict[str, Any],
                                          batch_size: int = None,
                                          ocr_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        优化的分批次处理切片数据
        
        Args:
            vision_image_data: Vision图像数据列表
            task_id: 任务ID
            drawing_id: 图纸ID
            shared_slice_results: 共享切片结果
            batch_size: 批次大小（默认使用配置）
            ocr_result: OCR结果
            
        Returns:
            处理结果
        """
        if not vision_image_data:
            return {"success": False, "error": "No vision image data provided"}
        
        # 使用配置化的批次大小
        if batch_size is None:
            batch_size = AnalysisSettings.MAX_SLICES_PER_BATCH
        
        total_slices = len(vision_image_data)
        total_batches = (total_slices + batch_size - 1) // batch_size
        
        logger.info(f"🔄 开始优化批次处理: {total_slices} 个切片，分为 {total_batches} 个批次")
        
        batch_results = []
        successful_batches = 0
        failed_batches = 0
        start_time = time.time()
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_slices)
            batch_data = vision_image_data[start_idx:end_idx]
            
            batch_task_id = f"{task_id}_batch_{batch_idx + 1}"
            
            # 使用标准化日志记录
            AnalysisLogger.log_batch_processing(batch_idx + 1, total_batches, len(batch_data))
            
            # 创建批次元数据
            batch_metadata = AnalysisMetadata(
                analysis_method="optimized_batch_processing",
                batch_id=batch_idx + 1,
                slice_count=len(batch_data),
                success=False,
                ocr_cache_used=self.ocr_cache_initialized
            )
            
            try:
                # 添加批次间延迟以避免API限制
                if batch_idx > 0:
                    time.sleep(AnalysisSettings.BATCH_PROCESSING_DELAY)
                
                # 处理单个批次
                batch_result = self._process_single_batch_optimized(
                    batch_data=batch_data,
                    batch_idx=batch_idx,
                    batch_task_id=batch_task_id,
                    shared_slice_results=shared_slice_results,
                    ocr_result=ocr_result,
                    metadata=batch_metadata
                )
                
                if batch_result.get("success"):
                    batch_results.append(batch_result)
                    successful_batches += 1
                    batch_metadata.success = True
                else:
                    failed_batches += 1
                    batch_metadata.error_message = batch_result.get("error", "未知错误")
                    logger.warning(f"⚠️ 批次 {batch_idx + 1} 处理失败: {batch_result.get('error')}")
                
                # 记录批次元数据
                batch_metadata.processing_time = time.time() - start_time
                AnalysisLogger.log_analysis_metadata(batch_metadata)
                
            except Exception as e:
                failed_batches += 1
                batch_metadata.error_message = str(e)
                batch_metadata.processing_time = time.time() - start_time
                AnalysisLogger.log_analysis_metadata(batch_metadata)
                logger.error(f"❌ 批次 {batch_idx + 1} 处理异常: {e}")
        
        # 合并批次结果
        if batch_results:
            merged_result = self._merge_batch_results_optimized(batch_results)
        else:
            merged_result = {"success": False, "error": "所有批次处理失败"}
        
        # 添加批次处理统计信息
        merged_result["batch_statistics"] = {
            "total_batches": total_batches,
            "successful_batches": successful_batches,
            "failed_batches": failed_batches,
            "batch_size": batch_size,
            "total_slices": total_slices,
            "ocr_cache_enabled": self.ocr_cache_initialized,
            "processing_time": time.time() - start_time,
            "success_rate": successful_batches / total_batches if total_batches > 0 else 0
        }
        
        # 记录缓存统计
        AnalysisLogger.log_cache_stats(self.ocr_cache.get_cache_stats())
        
        logger.info(f"✅ 优化批次处理完成: {successful_batches}/{total_batches} 个批次成功")
        
        return merged_result
    
    def _process_single_batch_optimized(self, 
                                      batch_data: List[Dict],
                                      batch_idx: int,
                                      batch_task_id: str,
                                      shared_slice_results: Dict[str, Any],
                                      ocr_result: Dict[str, Any] = None,
                                      metadata: AnalysisMetadata = None) -> Dict[str, Any]:
        """处理单个批次（优化版本）"""
        try:
            # 获取分析器实例（复用）
            from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
            dual_track_analyzer = self.analyzer_manager.get_analyzer(EnhancedGridSliceAnalyzer)
            
            # 重置批次状态
            self.analyzer_manager.reset_for_new_batch()
            
            # 传递OCR缓存给分析器
            if self.ocr_cache_initialized and self.global_ocr_cache:
                dual_track_analyzer._global_ocr_cache = self.global_ocr_cache.copy()
                logger.info(f"♻️ 批次 {batch_idx + 1} 使用全局OCR缓存: {len(self.global_ocr_cache)} 个切片")
            
            # 准备批次图像路径
            batch_image_paths = []
            for original_path, slice_result in shared_slice_results.items():
                if slice_result.get('sliced', False):
                    batch_image_paths.append(original_path)
                    break  # 只需要一个代表路径
            
            if not batch_image_paths:
                return {"success": False, "error": "无法获取批次图像路径"}
            
            # 创建批次绘图信息
            drawing_info = {
                "batch_id": batch_idx + 1,
                "slice_count": len(batch_data),
                "processing_method": "optimized_batch_dual_track",
                "ocr_cache_enabled": self.ocr_cache_initialized,
                "drawing_id": shared_slice_results.get("drawing_id", 0)
            }
            
            # 如果有OCR结果，添加相关信息
            if ocr_result:
                drawing_info["ocr_info"] = {
                    "has_merged_text": bool(ocr_result.get("merged_text_regions")),
                    "total_text_regions": len(ocr_result.get("merged_text_regions", [])),
                    "all_text_available": bool(ocr_result.get("all_text"))
                }
            
            # 执行双轨协同分析
            batch_result = dual_track_analyzer.analyze_drawing_with_dual_track(
                image_path=batch_image_paths[0],
                drawing_info=drawing_info,
                task_id=batch_task_id,
                output_dir=f"temp_batch_{batch_task_id}",
                shared_slice_results=shared_slice_results
            )
            
            # 第一个批次建立OCR缓存
            if batch_idx == 0 and not self.ocr_cache_initialized:
                if hasattr(dual_track_analyzer, '_global_ocr_cache') and dual_track_analyzer._global_ocr_cache:
                    self.global_ocr_cache = dual_track_analyzer._global_ocr_cache.copy()
                    self.ocr_cache_initialized = True
                    logger.info(f"🔄 建立全局OCR缓存: {len(self.global_ocr_cache)} 个切片")
            
            # 确保返回格式一致
            if batch_result.get("success"):
                qto_data = batch_result.get("qto_data", {})
                
                # 添加优化元数据
                if "analysis_metadata" not in qto_data:
                    qto_data["analysis_metadata"] = {}
                
                qto_data["analysis_metadata"].update({
                    "batch_id": batch_idx + 1,
                    "slice_count": len(batch_data),
                    "ocr_cache_used": self.ocr_cache_initialized,
                    "analyzer_reused": True,
                    "processing_method": "optimized_dual_track_analysis"
                })
                
                return {
                    "success": True,
                    "qto_data": qto_data
                }
            else:
                return {
                    "success": False,
                    "error": batch_result.get("error", "批次分析失败")
                }
            
        except Exception as e:
            logger.error(f"❌ 批次 {batch_idx + 1} 处理异常: {e}")
            return {"success": False, "error": str(e)}
    
    def _merge_batch_results_optimized(self, batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """优化的批次结果合并"""
        try:
            all_components = []
            total_processing_time = 0.0
            
            for batch_result in batch_results:
                if batch_result.get("success") and batch_result.get("qto_data"):
                    qto_data = batch_result["qto_data"]
                    components = qto_data.get("components", [])
                    all_components.extend(components)
                    
                    # 累积处理时间
                    metadata = qto_data.get("analysis_metadata", {})
                    total_processing_time += metadata.get("processing_time", 0.0)
            
            # 去重合并构件
            merged_components = self._deduplicate_components_optimized(all_components)
            
            # 生成合并结果
            merged_result = {
                "success": True,
                "qto_data": {
                    "components": merged_components,
                    "drawing_info": {},
                    "quantity_summary": self._calculate_quantity_summary_optimized(merged_components),
                    "analysis_metadata": {
                        "total_components": len(merged_components),
                        "original_components": len(all_components),
                        "deduplication_rate": 1 - (len(merged_components) / len(all_components)) if all_components else 0,
                        "total_processing_time": total_processing_time,
                        "merge_method": "optimized_batch_merge"
                    }
                }
            }
            
            logger.info(f"✅ 批次结果合并完成: {len(all_components)} → {len(merged_components)} 个构件")
            
            return merged_result
            
        except Exception as e:
            logger.error(f"❌ 批次结果合并失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _deduplicate_components_optimized(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化的构件去重"""
        if not components:
            return []
        
        # 使用组合键进行去重
        seen_keys = set()
        unique_components = []
        
        for component in components:
            # 生成唯一键
            component_id = component.get("component_id", "")
            component_type = component.get("component_type", "")
            location = component.get("location", {})
            
            # 位置信息用于去重
            x = location.get("global_x", location.get("x", 0)) if isinstance(location, dict) else 0
            y = location.get("global_y", location.get("y", 0)) if isinstance(location, dict) else 0
            
            # 创建唯一键（ID + 类型 + 大致位置）
            unique_key = f"{component_id}_{component_type}_{int(x//100)}_{int(y//100)}"
            
            if unique_key not in seen_keys:
                seen_keys.add(unique_key)
                unique_components.append(component)
        
        return unique_components
    
    def _calculate_quantity_summary_optimized(self, components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """优化的工程量汇总计算"""
        if not components:
            return {"total_count": 0, "component_types": {}}
        
        type_summary = {}
        total_volume = 0.0
        total_area = 0.0
        
        for component in components:
            comp_type = component.get("component_type", "未知")
            
            if comp_type not in type_summary:
                type_summary[comp_type] = {
                    "count": 0,
                    "volume": 0.0,
                    "area": 0.0
                }
            
            type_summary[comp_type]["count"] += 1
            
            # 提取体积和面积信息
            geometry = component.get("geometry", {})
            if isinstance(geometry, dict):
                volume = float(geometry.get("volume", 0))
                area = float(geometry.get("area", 0))
                
                type_summary[comp_type]["volume"] += volume
                type_summary[comp_type]["area"] += area
                total_volume += volume
                total_area += area
        
        return {
            "total_count": len(components),
            "total_volume": round(total_volume, 2),
            "total_area": round(total_area, 2),
            "component_types": type_summary
        }
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return {
            "analyzer_stats": self.analyzer_manager.get_instance_stats(),
            "cache_stats": self.ocr_cache.get_cache_stats(),
            "ocr_cache_initialized": self.ocr_cache_initialized,
            "global_cache_size": len(self.global_ocr_cache)
        } 