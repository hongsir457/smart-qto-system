#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸任务服务统一接口
提供向后兼容的接口封装
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# 向后兼容：重新导出原始函数
def process_drawing_celery_task(db_drawing_id: int, task_id: str):
    """图纸处理Celery任务（兼容接口）"""
    try:
        # 优先使用重构后的组件
        from .drawing_tasks_core import DrawingTasksCore
        core = DrawingTasksCore()
        return core.process_drawing_celery_task(db_drawing_id, task_id)
    except ImportError as e:
        logger.warning(f"⚠️ 重构组件导入失败: {e}, 回退到原版本")
        # 回退到原始版本
        from app.tasks.drawing_tasks import process_drawing_celery_task as legacy_task
        return legacy_task(db_drawing_id, task_id)

def batch_process_drawings_celery_task(drawing_tasks: list):
    """批量图纸处理Celery任务（兼容接口）"""
    try:
        # 优先使用重构后的组件
        from .drawing_tasks_core import DrawingTasksCore
        core = DrawingTasksCore()
        return core.batch_process_drawings_celery_task(drawing_tasks)
    except ImportError as e:
        logger.warning(f"⚠️ 重构组件导入失败: {e}, 回退到原版本")
        # 回退到原始版本
        from app.tasks.drawing_tasks import batch_process_drawings_celery_task as legacy_batch_task
        return legacy_batch_task(drawing_tasks)

# 服务类接口
class DrawingTasksService:
    """图纸任务服务类（重构后的统一接口）"""
    
    def __init__(self):
        """初始化图纸任务服务"""
        try:
            # 导入重构后的组件
            from .drawing_tasks_core import DrawingTasksCore
            from .drawing_image_processor import DrawingImageProcessor
            from .drawing_result_manager import DrawingResultManager
            
            # 初始化核心组件
            self.core = DrawingTasksCore()
            self.image_processor = DrawingImageProcessor(self.core)
            self.result_manager = DrawingResultManager(self.core)
            
            self.version = "refactored-2.0-modular"
            self.component_count = 3
            logger.info("✅ 使用重构后的模块化图纸任务服务")
            
        except ImportError as e:
            logger.warning(f"⚠️ 重构组件导入失败: {e}, 回退到原版本")
            # 回退标识
            self._legacy_mode = True
            self.version = "legacy-1275行巨无霸"
            self.component_count = 1

    def process_drawing(self, db_drawing_id: int, task_id: str):
        """处理图纸"""
        if hasattr(self, '_legacy_mode'):
            # 使用Legacy版本
            from app.tasks.drawing_tasks import process_drawing_celery_task
            return process_drawing_celery_task(db_drawing_id, task_id)
        else:
            # 使用重构版本
            return self.core.process_drawing_celery_task(db_drawing_id, task_id)

    def batch_process_drawings(self, drawing_tasks: list):
        """批量处理图纸"""
        if hasattr(self, '_legacy_mode'):
            # 使用Legacy版本
            from app.tasks.drawing_tasks import batch_process_drawings_celery_task
            return batch_process_drawings_celery_task(drawing_tasks)
        else:
            # 使用重构版本
            return self.core.batch_process_drawings_celery_task(drawing_tasks)

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        if hasattr(self, '_legacy_mode'):
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
                    'core': 'DrawingTasksCore',
                    'image_processor': 'DrawingImageProcessor',
                    'result_manager': 'DrawingResultManager'
                }
            })
            return status

    def cleanup(self):
        """清理资源"""
        if not hasattr(self, '_legacy_mode'):
            self.core.cleanup()
            self.image_processor.cleanup()
            self.result_manager.cleanup()

    def __del__(self):
        """析构函数"""
        self.cleanup()

# 向后兼容的导出
__all__ = [
    'DrawingTasksService', 
    'process_drawing_celery_task',
    'batch_process_drawings_celery_task'
] 