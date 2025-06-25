#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision服务包初始化
将重构后的Vision组件整合为统一的服务
"""

# 导入核心组件
from .vision_scanner_core import VisionScannerCore
from .vision_batch_processor import VisionBatchProcessor
from .vision_result_coordinator import VisionResultCoordinator

# 导出主要类
__all__ = [
    'VisionScannerCore',
    'VisionBatchProcessor', 
    'VisionResultCoordinator',
    'VisionScannerService'  # 兼容性接口
]

class VisionScannerService:
    """
    重构后的Vision扫描器统一接口
    整合所有Vision相关功能，保持向后兼容
    """
    
    def __init__(self):
        """初始化Vision扫描器服务"""
        # 初始化核心组件
        self.core = VisionScannerCore()
        
        # 直接从核心服务提供接口
        self.logger = self.core.logger
    
    # 主要接口方法：直接代理到核心组件
    async def scan_images_and_store(self, slice_data_list, drawing_id, batch_id=None):
        """扫描图像并存储结果"""
        return await self.core.scan_images_and_store(slice_data_list, drawing_id, batch_id)
    
    async def scan_images_with_shared_slices(self, shared_slice_data, drawing_id, batch_id=None):
        """使用共享切片数据扫描"""
        return await self.core.scan_images_with_shared_slices(shared_slice_data, drawing_id, batch_id)
    
    def validate_slice_data(self, slice_data):
        """验证切片数据"""
        return self.core.validate_slice_data(slice_data)
    
    def get_scanner_status(self):
        """获取扫描器状态"""
        return self.core.get_scanner_status()
    
    # 兼容性方法：保持原有接口名称
    def scan_slices_with_vision(self, *args, **kwargs):
        """已废弃的方法名，重定向到新接口"""
        import asyncio
        if hasattr(asyncio, 'run'):
            return asyncio.run(self.scan_images_and_store(*args, **kwargs))
        else:
            # Python 3.6 兼容性
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.scan_images_and_store(*args, **kwargs)) 