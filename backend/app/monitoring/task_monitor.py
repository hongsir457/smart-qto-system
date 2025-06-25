"""
任务监控器模块

负责监控任务执行状态、性能指标和错误统计
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict, deque


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消
    TIMEOUT = "timeout"      # 超时


@dataclass
class TaskMetrics:
    """任务指标数据类"""
    task_id: str
    task_type: str
    user_id: Optional[int]
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # 执行时长，秒
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    error_message: Optional[str] = None
    result_size_bytes: Optional[int] = None
    retry_count: int = 0
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskStatistics:
    """任务统计数据类"""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    pending_tasks: int
    cancelled_tasks: int
    timeout_tasks: int
    avg_duration: float
    success_rate: float
    error_rate: float
    throughput_per_hour: float
    peak_concurrent_tasks: int


class TaskMonitor:
    """
    任务监控器
    
    负责监控任务的执行状态、性能指标和统计信息
    """
    
    def __init__(self, 
                 max_task_history: int = 10000,
                 cleanup_interval: int = 3600,  # 1小时
                 max_history_hours: int = 72):   # 3天
        """
        初始化任务监控器
        
        Args:
            max_task_history: 最大任务历史记录数量
            cleanup_interval: 清理间隔，单位秒
            max_history_hours: 最大历史保存时间，单位小时
        """
        self.max_task_history = max_task_history
        self.cleanup_interval = cleanup_interval
        self.max_history_hours = max_history_hours
        
        self.task_metrics: Dict[str, TaskMetrics] = {}
        self.task_history: deque = deque(maxlen=max_task_history)
        self.active_tasks: Dict[str, TaskMetrics] = {}
        
        # 统计计数器
        self.task_counters = defaultdict(int)
        self.error_counters = defaultdict(int)
        self.user_task_counters = defaultdict(lambda: defaultdict(int))
        
        # 性能指标
        self.peak_concurrent_tasks = 0
        self.last_throughput_calculation = datetime.now()
        self.throughput_window = deque(maxlen=3600)  # 1小时窗口
        
        # 监控状态
        self._monitoring = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 告警回调
        self.alert_callbacks: List[Callable[[str, Dict], None]] = []
        
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self):
        """开始任务监控"""
        if self._monitoring:
            self.logger.warning("任务监控已在运行中")
            return
            
        self._monitoring = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        self.logger.info("任务监控已启动")
        
    def stop_monitoring(self):
        """停止任务监控"""
        if not self._monitoring:
            self.logger.warning("任务监控未在运行")
            return
            
        self._monitoring = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        self.logger.info("任务监控已停止")
        
    def start_task(self, 
                   task_type: str,
                   user_id: Optional[int] = None,
                   task_id: Optional[str] = None,
                   priority: int = 0,
                   tags: List[str] = None,
                   metadata: Dict[str, Any] = None) -> str:
        """
        开始监控任务
        
        Args:
            task_type: 任务类型
            user_id: 用户ID
            task_id: 任务ID，如果不提供则自动生成
            priority: 任务优先级
            tags: 任务标签
            metadata: 任务元数据
            
        Returns:
            任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
            
        if tags is None:
            tags = []
            
        if metadata is None:
            metadata = {}
            
        metrics = TaskMetrics(
            task_id=task_id,
            task_type=task_type,
            user_id=user_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            priority=priority,
            tags=tags,
            metadata=metadata
        )
        
        with self._lock:
            self.task_metrics[task_id] = metrics
            self.active_tasks[task_id] = metrics
            
            # 更新计数器
            self.task_counters['total'] += 1
            self.task_counters[task_type] += 1
            self.task_counters['running'] += 1
            
            if user_id:
                self.user_task_counters[user_id]['total'] += 1
                self.user_task_counters[user_id][task_type] += 1
                
            # 更新并发峰值
            concurrent = len(self.active_tasks)
            if concurrent > self.peak_concurrent_tasks:
                self.peak_concurrent_tasks = concurrent
                
        self.logger.info(f"开始监控任务: {task_id} (类型: {task_type}, 用户: {user_id})")
        return task_id
        
    def update_task_progress(self, 
                           task_id: str,
                           progress: float,
                           message: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 进度消息
            metadata: 额外元数据
        """
        with self._lock:
            if task_id not in self.task_metrics:
                self.logger.warning(f"任务不存在: {task_id}")
                return
                
            metrics = self.task_metrics[task_id]
            metrics.metadata['progress'] = progress
            
            if message:
                metrics.metadata['progress_message'] = message
                
            if metadata:
                metrics.metadata.update(metadata)
                
        self.logger.debug(f"任务进度更新: {task_id} -> {progress}%")
        
    def complete_task(self, 
                     task_id: str,
                     result_size_bytes: Optional[int] = None,
                     final_metadata: Optional[Dict[str, Any]] = None):
        """
        完成任务
        
        Args:
            task_id: 任务ID
            result_size_bytes: 结果大小，字节
            final_metadata: 最终元数据
        """
        with self._lock:
            if task_id not in self.task_metrics:
                self.logger.warning(f"任务不存在: {task_id}")
                return
                
            metrics = self.task_metrics[task_id]
            metrics.status = TaskStatus.COMPLETED
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            
            if result_size_bytes:
                metrics.result_size_bytes = result_size_bytes
                
            if final_metadata:
                metrics.metadata.update(final_metadata)
                
            # 移动到历史记录
            self.task_history.append(metrics)
            
            # 从活跃任务中移除
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
            # 更新计数器
            self.task_counters['completed'] += 1
            self.task_counters['running'] -= 1
            
            # 更新吞吐量
            self.throughput_window.append(datetime.now())
            
        self.logger.info(f"任务完成: {task_id} (耗时: {metrics.duration:.2f}秒)")
        
    def fail_task(self, 
                  task_id: str,
                  error_message: str,
                  error_type: Optional[str] = None):
        """
        标记任务失败
        
        Args:
            task_id: 任务ID
            error_message: 错误消息
            error_type: 错误类型
        """
        with self._lock:
            if task_id not in self.task_metrics:
                self.logger.warning(f"任务不存在: {task_id}")
                return
                
            metrics = self.task_metrics[task_id]
            metrics.status = TaskStatus.FAILED
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.error_message = error_message
            
            if error_type:
                metrics.metadata['error_type'] = error_type
                
            # 移动到历史记录
            self.task_history.append(metrics)
            
            # 从活跃任务中移除
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
            # 更新计数器
            self.task_counters['failed'] += 1
            self.task_counters['running'] -= 1
            self.error_counters[error_type or 'unknown'] += 1
            
        self.logger.error(f"任务失败: {task_id} - {error_message}")
        
        # 检查错误率告警
        self._check_error_rate_alerts()
        
    def cancel_task(self, task_id: str, reason: Optional[str] = None):
        """
        取消任务
        
        Args:
            task_id: 任务ID
            reason: 取消原因
        """
        with self._lock:
            if task_id not in self.task_metrics:
                self.logger.warning(f"任务不存在: {task_id}")
                return
                
            metrics = self.task_metrics[task_id]
            metrics.status = TaskStatus.CANCELLED
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            
            if reason:
                metrics.metadata['cancel_reason'] = reason
                
            # 移动到历史记录
            self.task_history.append(metrics)
            
            # 从活跃任务中移除
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                
            # 更新计数器
            self.task_counters['cancelled'] += 1
            self.task_counters['running'] -= 1
            
        self.logger.info(f"任务已取消: {task_id} - {reason}")
        
    def get_task_status(self, task_id: str) -> Optional[TaskMetrics]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务指标，如果任务不存在返回None
        """
        with self._lock:
            return self.task_metrics.get(task_id)
            
    def get_active_tasks(self) -> List[TaskMetrics]:
        """获取所有活跃任务"""
        with self._lock:
            return list(self.active_tasks.values())
            
    def get_task_statistics(self, hours: int = 1) -> TaskStatistics:
        """
        获取任务统计信息
        
        Args:
            hours: 统计最近几小时的数据
            
        Returns:
            任务统计信息
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # 从历史记录中筛选
            recent_tasks = [
                task for task in self.task_history
                if task.start_time >= cutoff_time
            ]
            
            # 计算统计信息
            total_tasks = len(recent_tasks)
            completed_tasks = len([t for t in recent_tasks if t.status == TaskStatus.COMPLETED])
            failed_tasks = len([t for t in recent_tasks if t.status == TaskStatus.FAILED])
            cancelled_tasks = len([t for t in recent_tasks if t.status == TaskStatus.CANCELLED])
            timeout_tasks = len([t for t in recent_tasks if t.status == TaskStatus.TIMEOUT])
            
            running_tasks = len(self.active_tasks)
            pending_tasks = 0  # 这里需要根据实际队列系统实现
            
            # 计算平均执行时长
            completed_durations = [t.duration for t in recent_tasks if t.duration is not None]
            avg_duration = sum(completed_durations) / len(completed_durations) if completed_durations else 0.0
            
            # 计算成功率和错误率
            success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
            error_rate = (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
            
            # 计算吞吐量
            throughput_per_hour = completed_tasks / hours if hours > 0 else 0.0
            
            return TaskStatistics(
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                running_tasks=running_tasks,
                pending_tasks=pending_tasks,
                cancelled_tasks=cancelled_tasks,
                timeout_tasks=timeout_tasks,
                avg_duration=avg_duration,
                success_rate=success_rate,
                error_rate=error_rate,
                throughput_per_hour=throughput_per_hour,
                peak_concurrent_tasks=self.peak_concurrent_tasks
            )
            
    def get_user_task_statistics(self, user_id: int, hours: int = 24) -> Dict:
        """
        获取用户任务统计
        
        Args:
            user_id: 用户ID
            hours: 统计时间范围，小时
            
        Returns:
            用户任务统计信息
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            user_tasks = [
                task for task in self.task_history
                if task.user_id == user_id and task.start_time >= cutoff_time
            ]
            
            total = len(user_tasks)
            completed = len([t for t in user_tasks if t.status == TaskStatus.COMPLETED])
            failed = len([t for t in user_tasks if t.status == TaskStatus.FAILED])
            
            # 按任务类型统计
            by_type = defaultdict(int)
            for task in user_tasks:
                by_type[task.task_type] += 1
                
            # 计算平均时长
            durations = [t.duration for t in user_tasks if t.duration is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            
            return {
                'user_id': user_id,
                'period_hours': hours,
                'total_tasks': total,
                'completed_tasks': completed,
                'failed_tasks': failed,
                'success_rate': (completed / total * 100) if total > 0 else 0.0,
                'avg_duration': avg_duration,
                'by_type': dict(by_type)
            }
            
    def get_error_statistics(self, hours: int = 24) -> Dict:
        """
        获取错误统计
        
        Args:
            hours: 统计时间范围，小时
            
        Returns:
            错误统计信息
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            failed_tasks = [
                task for task in self.task_history
                if task.status == TaskStatus.FAILED and task.start_time >= cutoff_time
            ]
            
            # 按错误类型统计
            error_types = defaultdict(int)
            error_messages = defaultdict(int)
            
            for task in failed_tasks:
                error_type = task.metadata.get('error_type', 'unknown')
                error_types[error_type] += 1
                
                if task.error_message:
                    error_messages[task.error_message] += 1
                    
            return {
                'period_hours': hours,
                'total_errors': len(failed_tasks),
                'error_types': dict(error_types),
                'common_errors': dict(sorted(
                    error_messages.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10])  # 前10个最常见错误
            }
            
    def get_performance_metrics(self, hours: int = 1) -> Dict:
        """
        获取性能指标
        
        Args:
            hours: 统计时间范围，小时
            
        Returns:
            性能指标
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_tasks = [
                task for task in self.task_history
                if task.start_time >= cutoff_time and task.duration is not None
            ]
            
            if not recent_tasks:
                return {
                    'period_hours': hours,
                    'message': '无性能数据'
                }
                
            durations = [t.duration for t in recent_tasks]
            memory_usages = [t.memory_usage_mb for t in recent_tasks if t.memory_usage_mb is not None]
            
            return {
                'period_hours': hours,
                'task_count': len(recent_tasks),
                'duration_stats': {
                    'min': min(durations),
                    'max': max(durations),
                    'avg': sum(durations) / len(durations),
                    'median': sorted(durations)[len(durations) // 2]
                },
                'memory_stats': {
                    'min': min(memory_usages) if memory_usages else 0,
                    'max': max(memory_usages) if memory_usages else 0,
                    'avg': sum(memory_usages) / len(memory_usages) if memory_usages else 0
                },
                'concurrent_peak': self.peak_concurrent_tasks
            }
            
    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """
        添加告警回调函数
        
        Args:
            callback: 告警回调函数
        """
        self.alert_callbacks.append(callback)
        
    def _check_error_rate_alerts(self):
        """检查错误率告警"""
        try:
            # 计算最近1小时的错误率
            stats = self.get_task_statistics(hours=1)
            
            # 错误率超过20%时告警
            if stats.error_rate > 20.0 and stats.total_tasks >= 10:
                alert = {
                    'type': 'high_error_rate',
                    'message': f'任务错误率过高: {stats.error_rate:.1f}%',
                    'error_rate': stats.error_rate,
                    'total_tasks': stats.total_tasks,
                    'failed_tasks': stats.failed_tasks
                }
                
                self.logger.warning(f"任务错误率告警: {alert['message']}")
                
                for callback in self.alert_callbacks:
                    try:
                        callback('high_error_rate', alert)
                    except Exception as e:
                        self.logger.error(f"告警回调执行失败: {e}")
                        
        except Exception as e:
            self.logger.error(f"检查错误率告警时发生错误: {e}")
            
    def _cleanup_loop(self):
        """清理循环"""
        self.logger.info("任务监控清理循环已启动")
        
        while self._monitoring:
            try:
                self._cleanup_old_tasks()
                
            except Exception as e:
                self.logger.error(f"任务监控清理循环中发生错误: {e}")
                
            time.sleep(self.cleanup_interval)
            
    def _cleanup_old_tasks(self):
        """清理过期任务"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_history_hours)
        
        with self._lock:
            # 清理过期的任务指标
            expired_task_ids = [
                task_id for task_id, metrics in self.task_metrics.items()
                if metrics.start_time < cutoff_time and task_id not in self.active_tasks
            ]
            
            for task_id in expired_task_ids:
                del self.task_metrics[task_id]
                
            # 清理过期的吞吐量数据
            cutoff_throughput = datetime.now() - timedelta(hours=1)
            while self.throughput_window and self.throughput_window[0] < cutoff_throughput:
                self.throughput_window.popleft()
                
            if expired_task_ids:
                self.logger.debug(f"清理了 {len(expired_task_ids)} 个过期任务记录")
                
    def is_monitoring(self) -> bool:
        """检查是否正在监控"""
        return self._monitoring
        
    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        
        with self._lock:
            self.task_metrics.clear()
            self.task_history.clear()
            self.active_tasks.clear()
            self.task_counters.clear()
            self.error_counters.clear()
            self.user_task_counters.clear()
            self.throughput_window.clear()
            self.alert_callbacks.clear()
            
        self.logger.info("任务监控器已清理") 