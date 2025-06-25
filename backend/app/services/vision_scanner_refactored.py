#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision Scanner Service (重构版) - 作为新架构的代理接口
保持向后兼容性，将原有大文件重构为小组件
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional

# 导入重构后的Vision组件
from .vision import VisionScannerService as NewVisionScanner

logger = logging.getLogger(__name__)

class VisionScannerService:
    """
    Vision扫描器服务（重构版）
    作为原有VisionScannerService的代理，调用重构后的组件
    """
    
    def __init__(self):
        """初始化Vision扫描器服务"""
        # 使用重构后的Vision扫描器
        self._new_scanner = NewVisionScanner()
        
        # 保持原有属性的兼容性
        self.logger = self._new_scanner.logger
        
        logger.info("✅ Vision Scanner Service (重构版) 初始化完成")

    async def scan_images_and_store(self, 
                                  slice_data_list: List[Dict[str, Any]], 
                                  drawing_id: int,
                                  batch_id: str = None) -> Dict[str, Any]:
        """扫描图像切片并存储结果"""
        return await self._new_scanner.scan_images_and_store(slice_data_list, drawing_id, batch_id)

    async def scan_images_with_shared_slices(self, 
                                           shared_slice_data: Dict[str, Any],
                                           drawing_id: int,
                                           batch_id: str = None) -> Dict[str, Any]:
        """使用共享切片数据进行扫描"""
        return await self._new_scanner.scan_images_with_shared_slices(shared_slice_data, drawing_id, batch_id)

    def validate_slice_data(self, slice_data: Dict[str, Any]) -> bool:
        """验证切片数据的完整性"""
        return self._new_scanner.validate_slice_data(slice_data)

    def get_scanner_status(self) -> Dict[str, Any]:
        """获取扫描器状态信息"""
        return self._new_scanner.get_scanner_status()

    # 兼容性方法：保持原有接口
    def scan_slices_with_vision(self, slice_data_list, drawing_id, batch_id=None):
        """旧接口名称的兼容性支持"""
        logger.warning("⚠️ scan_slices_with_vision方法已废弃，请使用scan_images_and_store")
        
        # 如果在异步上下文中，直接调用
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(
                self.scan_images_and_store(slice_data_list, drawing_id, batch_id)
            )
        except RuntimeError:
            # 如果不在异步上下文中，创建新的事件循环
            return asyncio.run(
                self.scan_images_and_store(slice_data_list, drawing_id, batch_id)
            )

    # 废弃方法的占位符
    def process_single_slice(self, *args, **kwargs):
        """已废弃的单切片处理方法"""
        raise NotImplementedError("单切片处理方法已废弃，请使用批次处理")

    def merge_slice_results(self, *args, **kwargs):
        """已废弃的切片结果合并方法"""
        raise NotImplementedError("切片结果合并方法已废弃，功能已集成到批次处理中")

    def extract_components_from_vision_response(self, *args, **kwargs):
        """已废弃的响应解析方法"""
        raise NotImplementedError("响应解析方法已废弃，功能已集成到AI分析器中")


# 兼容性：创建别名
VisionScanner = VisionScannerService 