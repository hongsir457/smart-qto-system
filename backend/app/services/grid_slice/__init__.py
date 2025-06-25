#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网格切片分析器统一接口
提供向后兼容的接口封装
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EnhancedGridSliceAnalyzer:
    """增强版网格切片分析器（重构后的统一接口）"""
    
    def __init__(self, slice_size: int = 1024, overlap: int = 128):
        """初始化增强分析器"""
        try:
            # 导入重构后的组件
            from .grid_slice_analyzer_core import GridSliceAnalyzerCore
            from .grid_slice_ocr_processor import GridSliceOCRProcessor
            from .grid_slice_vision_analyzer import GridSliceVisionAnalyzer
            from .grid_slice_coordinate_manager import GridSliceCoordinateManager
            from .grid_slice_result_merger import GridSliceResultMerger
            
            # 初始化核心组件
            self.core = GridSliceAnalyzerCore(slice_size, overlap)
            self.ocr_processor = GridSliceOCRProcessor(self.core)
            self.vision_analyzer = GridSliceVisionAnalyzer(self.core)
            self.coordinate_manager = GridSliceCoordinateManager(self.core)
            self.result_merger = GridSliceResultMerger(self.core)
            
            self.version = "refactored-2.0-modular"
            self.component_count = 5
            logger.info("✅ 使用重构后的模块化网格切片分析器")
            
        except ImportError as e:
            logger.warning(f"⚠️ 重构组件导入失败: {e}, 回退到原版本")
            # 回退到原始版本
            from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer as LegacyAnalyzer
            self._legacy_analyzer = LegacyAnalyzer(slice_size, overlap)
            self.version = "legacy-2017行巨无霸"
            self.component_count = 1

    def analyze_drawing_with_dual_track(self, 
                                      image_path: str,
                                      drawing_info: Dict[str, Any],
                                      task_id: str,
                                      output_dir: str = "temp_slices",
                                      shared_slice_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行双轨协同分析"""
        if hasattr(self, '_legacy_analyzer'):
            # 使用Legacy版本
            return self._legacy_analyzer.analyze_drawing_with_dual_track(
                image_path, drawing_info, task_id, output_dir, shared_slice_results
            )
        else:
            # 使用重构版本
            return self.core.analyze_drawing_with_dual_track(
                image_path, drawing_info, task_id, output_dir, shared_slice_results
            )

    def reset_batch_state(self):
        """重置批次状态"""
        if hasattr(self, '_legacy_analyzer'):
            return self._legacy_analyzer.reset_batch_state()
        else:
            return self.core.reset_batch_state()

    def get_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        if hasattr(self, '_legacy_analyzer'):
            return {
                'version': self.version,
                'architecture': 'legacy',
                'component_count': self.component_count,
                'status': 'available'
            }
        else:
            status = self.core.get_status()
            status.update({
                'architecture': 'modular',
                'component_count': self.component_count,
                'components': {
                    'core': 'GridSliceAnalyzerCore',
                    'ocr_processor': 'GridSliceOCRProcessor', 
                    'vision_analyzer': 'GridSliceVisionAnalyzer',
                    'coordinate_manager': 'GridSliceCoordinateManager',
                    'result_merger': 'GridSliceResultMerger'
                }
            })
            return status

    def cleanup(self):
        """清理资源"""
        if hasattr(self, '_legacy_analyzer'):
            if hasattr(self._legacy_analyzer, 'cleanup'):
                self._legacy_analyzer.cleanup()
        else:
            self.core.cleanup()
            # 清理其他组件
            for component in [self.ocr_processor, self.vision_analyzer, 
                            self.coordinate_manager, self.result_merger]:
                if hasattr(component, 'cleanup'):
                    component.cleanup()

    def __del__(self):
        """析构函数"""
        self.cleanup()

# 向后兼容的导出
__all__ = ['EnhancedGridSliceAnalyzer'] 