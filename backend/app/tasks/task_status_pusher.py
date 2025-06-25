# -*- coding: utf-8 -*-
"""
任务状态推送器
集成Celery和WebSocket，实现任务状态的实时推送
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_retry, task_revoked
import threading
import inspect

from .real_time_task_manager import RealTimeTaskManager, TaskStatus, TaskStage

logger = logging.getLogger(__name__)

class TaskStatusPusher:
    """任务状态推送器"""
    
    def __init__(self, task_manager: RealTimeTaskManager, celery_app: Celery = None):
        self.task_manager = task_manager
        # 如果没有提供celery_app，则使用中心化的实例
        if celery_app is None:
            try:
                from app.core.celery_app import celery_app as central_celery_app
                self.celery_app = central_celery_app
                logger.info("使用中心化的Celery应用实例")
            except ImportError:
                logger.warning("无法导入中心化的Celery应用实例")
                self.celery_app = None
        else:
            self.celery_app = celery_app
            
        self._running = False
        self._monitoring_thread = None
        
        # 设置Celery信号处理器
        self._setup_celery_signals()
    
    def _setup_celery_signals(self):
        """设置Celery信号处理器"""
        
        @task_prerun.connect
        def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
            """任务开始前的处理"""
            task_name = getattr(task, 'name', 'Unknown Task')
            user_id = kwargs.get('user_id') if kwargs else None
            
            # 如果kwargs中没有user_id，尝试从位置参数解析
            if user_id is None and args:
                try:
                    sig = inspect.signature(task.run if hasattr(task, 'run') else task)
                    param_list = list(sig.parameters.keys())
                    if 'user_id' in param_list:
                        index = param_list.index('user_id')
                        if len(args) > index and isinstance(args[index], int):
                            user_id = args[index]
                except Exception as e:
                    logger.debug(f"解析user_id失败: {e}")
            
            # 如果任务不存在则创建
            if not self.task_manager.get_task(task_id):
                self.task_manager.create_task(
                    task_id=task_id,
                    name=task_name,
                    user_id=user_id,
                    metadata={'celery_task_name': task_name}
                )
            
            # 更新为开始状态
            self._run_async(self.task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.STARTED,
                stage=TaskStage.QUEUED,
                message="任务开始执行"
            ))
            
            logger.info(f"Celery任务开始: {task_id} - {task_name}")
        
        @task_postrun.connect
        def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
            """任务完成后的处理"""
            if state == 'SUCCESS':
                results = retval if isinstance(retval, dict) else {'result': retval}
                self._run_async(self.task_manager.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.SUCCESS,
                    stage=TaskStage.COMPLETED,
                    progress=100,
                    message="任务执行成功",
                    results=results
                ))
                logger.info(f"Celery任务成功完成: {task_id}")
        
        @task_failure.connect
        def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
            """任务失败的处理"""
            error_message = str(exception) if exception else "未知错误"
            self._run_async(self.task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                stage=TaskStage.FAILED,
                message="任务执行失败",
                error_message=error_message
            ))
            logger.error(f"Celery任务失败: {task_id} - {error_message}")
        
        @task_retry.connect
        def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
            """任务重试的处理"""
            retry_message = str(reason) if reason else "任务重试"
            self._run_async(self.task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.RETRY,
                message=f"任务重试: {retry_message}"
            ))
            logger.info(f"Celery任务重试: {task_id} - {retry_message}")
        
        @task_revoked.connect
        def task_revoked_handler(sender=None, task_id=None, terminated=None, signum=None, expired=None, **kwds):
            """任务被撤销的处理"""
            revoke_reason = "任务被撤销"
            if terminated:
                revoke_reason = "任务被终止"
            elif expired:
                revoke_reason = "任务已过期"
            
            self._run_async(self.task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.REVOKED,
                stage=TaskStage.FAILED,
                message=revoke_reason,
                error_message=revoke_reason
            ))
            logger.info(f"Celery任务被撤销: {task_id} - {revoke_reason}")
    
    async def update_task_progress(self, task_id: str, progress: int, 
                                 stage: TaskStage = None, message: str = None):
        """更新任务进度"""
        await self.task_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            stage=stage,
            progress=progress,
            message=message
        )
    
    async def push_custom_update(self, task_id: str, status: TaskStatus = None,
                               stage: TaskStage = None, progress: int = None,
                               message: str = None, results: Dict = None):
        """推送自定义更新"""
        await self.task_manager.update_task_status(
            task_id=task_id,
            status=status or TaskStatus.PROCESSING,
            stage=stage,
            progress=progress,
            message=message,
            results=results
        )
    
    def create_task_with_tracking(self, name: str, user_id: int = None, 
                                metadata: Dict = None) -> str:
        """创建带跟踪的任务"""
        return self.task_manager.create_task(
            name=name,
            user_id=user_id,
            metadata=metadata or {}
        )
    
    def start_monitoring(self):
        """开始监控任务状态"""
        if self._running:
            return
        
        self._running = True
        self._monitoring_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
        self._monitoring_thread.start()
        logger.info("任务状态监控已启动")
    
    def stop_monitoring(self):
        """停止监控任务状态"""
        self._running = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        logger.info("任务状态监控已停止")
    
    def _monitor_tasks(self):
        """监控任务状态的后台线程"""
        while self._running:
            try:
                # 清理过期任务
                asyncio.run(self.task_manager.cleanup_expired_tasks())
                
                # 检查长时间运行的任务
                self._check_stale_tasks()
                
            except Exception as e:
                logger.error(f"任务监控出错: {e}")
            
            # 每5分钟执行一次
            threading.Event().wait(300)
    
    def _check_stale_tasks(self):
        """检查长时间运行的任务"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=2)  # 2小时超时
        active_tasks = self.task_manager.get_active_tasks()
        
        for task in active_tasks:
            if task.started_at and task.started_at < cutoff_time:
                # 标记为失败
                asyncio.run(self.task_manager.update_task_status(
                    task_id=task.task_id,
                    status=TaskStatus.FAILURE,
                    stage=TaskStage.FAILED,
                    message="任务执行超时",
                    error_message="任务执行时间超过2小时"
                ))
                logger.warning(f"任务执行超时: {task.task_id}")

    # ------------------------------------------------------------------
    # 内部工具：在有/无事件循环环境下安全运行协程
    # ------------------------------------------------------------------
    @staticmethod
    def _run_async(coro):
        """在当前事件循环或新事件循环中运行协程。"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(coro)
            else:
                asyncio.run(coro)
        except RuntimeError:
            asyncio.run(coro)

class ProgressTracker:
    """进度跟踪器 - 用于在任务内部更新进度"""
    
    def __init__(self, task_id: str, pusher: TaskStatusPusher):
        self.task_id = task_id
        self.pusher = pusher
        self.current_progress = 0
    
    async def update_progress(self, progress: int, stage: TaskStage = None, 
                            message: str = None):
        """更新进度"""
        self.current_progress = progress
        await self.pusher.update_task_progress(
            task_id=self.task_id,
            progress=progress,
            stage=stage,
            message=message
        )
    
    async def update_stage(self, stage: TaskStage, message: str = None, 
                         progress: int = None):
        """更新阶段"""
        if progress is not None:
            self.current_progress = progress
        
        await self.pusher.update_task_progress(
            task_id=self.task_id,
            progress=progress or self.current_progress,
            stage=stage,
            message=message
        )
    
    async def increment_progress(self, increment: int = 1, stage: TaskStage = None,
                               message: str = None):
        """增加进度"""
        self.current_progress = min(100, self.current_progress + increment)
        await self.pusher.update_task_progress(
            task_id=self.task_id,
            progress=self.current_progress,
            stage=stage,
            message=message
        )
    
    async def complete(self, results: Dict = None, message: str = "任务完成"):
        """标记完成"""
        await self.pusher.push_custom_update(
            task_id=self.task_id,
            status=TaskStatus.SUCCESS,
            stage=TaskStage.COMPLETED,
            progress=100,
            message=message,
            results=results
        )
    
    async def fail(self, error_message: str, message: str = "任务失败"):
        """标记失败"""
        await self.pusher.task_manager.update_task_status(
            task_id=self.task_id,
            status=TaskStatus.FAILURE,
            stage=TaskStage.FAILED,
            message=message,
            error_message=error_message
        )

# 装饰器用于自动跟踪任务进度
def track_progress(task_name: str = None, user_id_param: str = 'user_id'):
    """
    装饰器：自动跟踪Celery任务进度
    
    Args:
        task_name: 任务名称
        user_id_param: 用户ID参数名称
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取任务ID和用户ID
            task_id = func.request.id if hasattr(func, 'request') else None
            user_id = kwargs.get(user_id_param)
            
            if not task_id:
                return func(*args, **kwargs)
            
            # 创建进度跟踪器
            from . import status_pusher
            tracker = ProgressTracker(task_id, status_pusher)
            
            # 将跟踪器添加到kwargs中
            kwargs['progress_tracker'] = tracker
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # 在失败时更新状态
                asyncio.run(tracker.fail(str(e)))
                raise
        
        return wrapper
    return decorator 