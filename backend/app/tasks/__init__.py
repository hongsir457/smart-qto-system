# -*- coding: utf-8 -*-
"""
任务管理系统初始化模块
提供实时任务状态跟踪和WebSocket推送功能
"""

import logging

# 从正确的路径导入 Celery app 实例
from ..core.celery_app import celery_app
from .real_time_task_manager import (
    RealTimeTaskManager, 
    TaskInfo, 
    TaskStatus, 
    TaskStage
)
from .task_status_pusher import (
    TaskStatusPusher, 
    ProgressTracker,
    track_progress
)

# 1. 首先创建全局唯一的 TaskManager 实例。
# 这样，当其他模块（如drawing_tasks）从这个包导入时，task_manager 已经存在。
task_manager = RealTimeTaskManager()

# 2. 接着创建依赖于 task_manager 的 status_pusher。
status_pusher = TaskStatusPusher(task_manager)

# 3. 然后，再导入依赖于上面实例的模块。
# 这打破了 A -> B -> A 的循环导入。
from .drawing_tasks import (
    process_drawing_celery_task
)

# 注意：监控将在FastAPI startup事件中启动，而不是在模块导入时

# 4. 定义 __all__ 用于 'from . import *'
__all__ = [
    'celery_app',
    'task_manager',
    'status_pusher',
    'RealTimeTaskManager',
    'TaskStatusPusher',
    'TaskInfo',
    'TaskStatus',
    'TaskStage',
    'ProgressTracker',
    'track_progress',
    'process_drawing_celery_task'
] 