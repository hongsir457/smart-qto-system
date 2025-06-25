#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision扫描器核心组件
负责核心扫描服务和配置管理
"""
import logging
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class VisionScannerCore:
    """Vision扫描器核心类"""
    
    def __init__(self):
        """初始化Vision扫描器"""
        self.logger = logger
        logger.info("✅ Vision Scanner Core 初始化完成")

    async def scan_images_and_store(self, 
                                  slice_data_list: List[Dict[str, Any]], 
                                  drawing_id: int,
                                  batch_id: str = None) -> Dict[str, Any]:
        """
        扫描图像切片并存储结果
        
        Args:
            slice_data_list: 切片数据列表
            drawing_id: 图纸ID  
            batch_id: 批次ID
            
        Returns:
            扫描结果字典
        """
        logger.info(f"🔍 开始Vision扫描 - 图纸ID: {drawing_id}, 切片数量: {len(slice_data_list)}")
        start_time = time.time()
        
        try:
            # 导入AI分析器
            from app.services.ai import AIAnalyzer
            ai_analyzer = AIAnalyzer()
            
            if not ai_analyzer.is_available():
                logger.error("❌ AI分析服务不可用")
                return {
                    "success": False, 
                    "error": "AI分析服务不可用",
                    "components": []
                }
            
            # 导入批次处理器
            from .vision_batch_processor import VisionBatchProcessor
            batch_processor = VisionBatchProcessor(ai_analyzer)
            
            # 处理切片批次
            batch_results = await batch_processor.process_slices_in_batches(
                slice_data_list, drawing_id, batch_id
            )
            
            if not batch_results.get("success", False):
                logger.error(f"❌ 批次处理失败: {batch_results.get('error', 'Unknown error')}")
                return batch_results
            
            # 导入结果协调器
            from .vision_result_coordinator import VisionResultCoordinator
            result_coordinator = VisionResultCoordinator()
            
            # 合并和协调结果
            final_result = await result_coordinator.merge_and_store_results(
                batch_results, drawing_id, batch_id
            )
            
            processing_time = time.time() - start_time
            final_result["processing_time"] = processing_time
            
            logger.info(f"✅ Vision扫描完成 - 用时: {processing_time:.2f}s, 构件数量: {len(final_result.get('components', []))}")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Vision扫描异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "components": [],
                "processing_time": time.time() - start_time
            }

    async def scan_images_with_shared_slices(self, 
                                           shared_slice_data: Dict[str, Any],
                                           drawing_id: int,
                                           batch_id: str = None) -> Dict[str, Any]:
        """
        使用共享切片数据进行扫描
        
        Args:
            shared_slice_data: 共享切片数据
            drawing_id: 图纸ID
            batch_id: 批次ID
            
        Returns:
            扫描结果字典
        """
        logger.info(f"🔍 开始共享切片Vision扫描 - 图纸ID: {drawing_id}")
        
        try:
            # 提取切片列表
            slice_list = shared_slice_data.get("slices", [])
            slice_metadata = shared_slice_data.get("metadata", {})
            
            if not slice_list:
                logger.warning("⚠️ 共享切片数据为空")
                return {
                    "success": False,
                    "error": "共享切片数据为空",
                    "components": []
                }
            
            # 转换为标准切片数据格式
            slice_data_list = []
            for i, slice_info in enumerate(slice_list):
                slice_data = {
                    "slice_id": f"shared_slice_{i}",
                    "image_path": slice_info.get("image_path"),
                    "bounds": slice_info.get("bounds"),
                    "metadata": slice_info.get("metadata", {}),
                    "shared_metadata": slice_metadata
                }
                slice_data_list.append(slice_data)
            
            # 调用标准扫描方法
            return await self.scan_images_and_store(slice_data_list, drawing_id, batch_id)
            
        except Exception as e:
            logger.error(f"❌ 共享切片扫描异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "components": []
            }

    def validate_slice_data(self, slice_data: Dict[str, Any]) -> bool:
        """验证切片数据的完整性"""
        required_fields = ["slice_id", "image_path"]
        
        for field in required_fields:
            if field not in slice_data:
                logger.error(f"❌ 切片数据缺少必要字段: {field}")
                return False
        
        # 检查图像文件是否存在
        image_path = slice_data.get("image_path")
        if image_path and not Path(image_path).exists():
            logger.error(f"❌ 切片图像文件不存在: {image_path}")
            return False
        
        return True

    def get_scanner_status(self) -> Dict[str, Any]:
        """获取扫描器状态信息"""
        return {
            "service_name": "VisionScannerCore",
            "status": "active",
            "capabilities": [
                "slice_scanning",
                "batch_processing", 
                "shared_slice_support",
                "result_coordination"
            ],
            "supported_formats": ["PNG", "JPEG", "WebP"],
            "max_batch_size": 20,
            "version": "2.0.0"
        } 