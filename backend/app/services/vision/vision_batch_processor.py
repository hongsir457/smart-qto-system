#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision批次处理器组件
负责图像切片的批次处理和任务管理
"""
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VisionBatchProcessor:
    """Vision批次处理器"""
    
    def __init__(self, ai_analyzer):
        """初始化批次处理器"""
        self.ai_analyzer = ai_analyzer
        self.batch_size = 10  # 默认批次大小
        self.max_concurrent = 3  # 最大并发数
        
    async def process_slices_in_batches(self, 
                                      slice_data_list: List[Dict[str, Any]], 
                                      drawing_id: int,
                                      batch_id: str = None) -> Dict[str, Any]:
        """
        分批处理图像切片
        
        Args:
            slice_data_list: 切片数据列表
            drawing_id: 图纸ID
            batch_id: 批次ID
            
        Returns:
            批次处理结果
        """
        logger.info(f"📦 开始批次处理 - 总切片数: {len(slice_data_list)}, 批次大小: {self.batch_size}")
        
        try:
            # 分割切片到批次
            batches = self._split_into_batches(slice_data_list, self.batch_size)
            logger.info(f"📊 已分割为 {len(batches)} 个批次")
            
            # 处理每个批次
            all_batch_results = []
            failed_batches = []
            
            for batch_index, batch_slices in enumerate(batches):
                logger.info(f"🔄 处理批次 {batch_index + 1}/{len(batches)} - 切片数: {len(batch_slices)}")
                
                try:
                    batch_result = await self._process_single_batch(
                        batch_slices, batch_index, drawing_id, batch_id
                    )
                    
                    if batch_result.get("success", False):
                        all_batch_results.append(batch_result)
                        logger.info(f"✅ 批次 {batch_index + 1} 处理成功")
                    else:
                        failed_batches.append({
                            "batch_index": batch_index,
                            "error": batch_result.get("error", "Unknown error"),
                            "slice_count": len(batch_slices)
                        })
                        logger.error(f"❌ 批次 {batch_index + 1} 处理失败: {batch_result.get('error')}")
                        
                except Exception as e:
                    failed_batches.append({
                        "batch_index": batch_index,
                        "error": str(e),
                        "slice_count": len(batch_slices)
                    })
                    logger.error(f"❌ 批次 {batch_index + 1} 处理异常: {e}")
                
                # 批次间短暂延迟，避免API过载
                if batch_index < len(batches) - 1:
                    await asyncio.sleep(0.5)
            
            # 合并批次结果
            merged_result = self._merge_batch_results(all_batch_results, failed_batches)
            
            success_rate = len(all_batch_results) / len(batches) if batches else 0
            logger.info(f"📈 批次处理完成 - 成功率: {success_rate:.1%} ({len(all_batch_results)}/{len(batches)})")
            
            return merged_result
            
        except Exception as e:
            logger.error(f"❌ 批次处理器异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "components": [],
                "batch_summary": {
                    "total_batches": 0,
                    "successful_batches": 0,
                    "failed_batches": 0
                }
            }

    def _split_into_batches(self, data_list: List[Dict], batch_size: int) -> List[List[Dict]]:
        """将数据列表分割为批次"""
        batches = []
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            batches.append(batch)
        return batches

    async def _process_single_batch(self, 
                                  batch_slices: List[Dict[str, Any]], 
                                  batch_index: int,
                                  drawing_id: int,
                                  batch_id: str = None) -> Dict[str, Any]:
        """
        处理单个批次
        
        Args:
            batch_slices: 批次中的切片列表
            batch_index: 批次索引
            drawing_id: 图纸ID
            batch_id: 批次ID
            
        Returns:
            单个批次的处理结果
        """
        batch_start_time = time.time()
        
        try:
            # 准备图像路径列表
            image_paths = []
            slice_metadata_list = []
            
            for slice_data in batch_slices:
                image_path = slice_data.get("image_path")
                if image_path and Path(image_path).exists():
                    image_paths.append(image_path)
                    slice_metadata_list.append({
                        "slice_id": slice_data.get("slice_id"),
                        "bounds": slice_data.get("bounds"),
                        "metadata": slice_data.get("metadata", {})
                    })
                else:
                    logger.warning(f"⚠️ 跳过无效切片: {slice_data.get('slice_id', 'unknown')}")
            
            if not image_paths:
                logger.warning(f"⚠️ 批次 {batch_index} 中没有有效图像")
                return {
                    "success": False,
                    "error": "批次中没有有效图像",
                    "components": [],
                    "batch_info": {
                        "batch_index": batch_index,
                        "slice_count": len(batch_slices),
                        "valid_images": 0
                    }
                }
            
            # 调用AI分析器进行Vision分析
            context_data = {
                "drawing_id": drawing_id,
                "batch_id": batch_id,
                "batch_index": batch_index,
                "slice_metadata": slice_metadata_list
            }
            
            analysis_result = self.ai_analyzer.generate_qto_from_local_images(
                image_paths, context_data
            )
            
            # 处理分析结果
            if analysis_result.get("success", False):
                qto_data = analysis_result.get("qto_data", {})
                components = qto_data.get("components", [])
                
                # 为每个构件添加批次信息
                for component in components:
                    component["batch_index"] = batch_index
                    component["source_batch_id"] = batch_id
                
                batch_result = {
                    "success": True,
                    "components": components,
                    "batch_info": {
                        "batch_index": batch_index,
                        "slice_count": len(batch_slices),
                        "valid_images": len(image_paths),
                        "component_count": len(components),
                        "processing_time": time.time() - batch_start_time
                    },
                    "qto_metadata": qto_data.get("analysis_metadata", {})
                }
                
                logger.info(f"✅ 批次 {batch_index} 分析完成: {len(components)} 个构件")
                return batch_result
                
            else:
                error_msg = analysis_result.get("error", "AI分析失败")
                logger.error(f"❌ 批次 {batch_index} AI分析失败: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "components": [],
                    "batch_info": {
                        "batch_index": batch_index,
                        "slice_count": len(batch_slices),
                        "valid_images": len(image_paths)
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ 批次 {batch_index} 处理异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "components": [],
                "batch_info": {
                    "batch_index": batch_index,
                    "slice_count": len(batch_slices),
                    "processing_time": time.time() - batch_start_time
                }
            }

    def _merge_batch_results(self, 
                           successful_results: List[Dict[str, Any]], 
                           failed_batches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并批次结果
        
        Args:
            successful_results: 成功的批次结果列表
            failed_batches: 失败的批次信息列表
            
        Returns:
            合并后的总体结果
        """
        try:
            # 合并所有成功批次的构件
            all_components = []
            total_processing_time = 0
            batch_summaries = []
            
            for result in successful_results:
                components = result.get("components", [])
                all_components.extend(components)
                
                batch_info = result.get("batch_info", {})
                total_processing_time += batch_info.get("processing_time", 0)
                batch_summaries.append(batch_info)
            
            # 去重处理（基于构件ID和位置）
            unique_components = self._remove_duplicate_components(all_components)
            
            # 构建合并结果
            merged_result = {
                "success": len(successful_results) > 0,
                "components": unique_components,
                "batch_summary": {
                    "total_batches": len(successful_results) + len(failed_batches),
                    "successful_batches": len(successful_results),
                    "failed_batches": len(failed_batches),
                    "total_components": len(all_components),
                    "unique_components": len(unique_components),
                    "total_processing_time": total_processing_time
                },
                "batch_details": batch_summaries,
                "failed_batch_details": failed_batches
            }
            
            if failed_batches:
                merged_result["warnings"] = [
                    f"有 {len(failed_batches)} 个批次处理失败"
                ]
            
            logger.info(f"🔄 批次结果合并完成: {len(unique_components)} 个唯一构件")
            return merged_result
            
        except Exception as e:
            logger.error(f"❌ 批次结果合并异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"批次结果合并失败: {str(e)}",
                "components": [],
                "batch_summary": {
                    "total_batches": len(successful_results) + len(failed_batches),
                    "successful_batches": 0,
                    "failed_batches": len(successful_results) + len(failed_batches)
                }
            }

    def _remove_duplicate_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """移除重复构件"""
        if not components:
            return []
        
        unique_components = []
        seen_keys = set()
        
        for component in components:
            # 生成构件的唯一标识
            component_id = component.get("component_id", "")
            location = component.get("location", "")
            dimensions = component.get("dimensions", {})
            
            # 创建唯一键
            unique_key = f"{component_id}_{location}_{hash(str(dimensions))}"
            
            if unique_key not in seen_keys:
                seen_keys.add(unique_key)
                unique_components.append(component)
            else:
                logger.debug(f"🔄 移除重复构件: {component_id}")
        
        if len(unique_components) < len(components):
            logger.info(f"🧹 去重完成: {len(components)} → {len(unique_components)} 个构件")
        
        return unique_components

    def _safe_convert_to_number(self, value: Any, default: float = 0.0) -> float:
        """安全转换值为数字"""
        if value is None:
            return default
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                # 移除可能的单位和空格
                clean_value = value.strip().replace('mm', '').replace('m', '').replace('kg', '')
                return float(clean_value)
            except ValueError:
                return default
        
        return default 