"""
性能监控器模块

负责监控系统性能指标，包括CPU使用率、内存使用量、磁盘I/O等
"""

import time
import logging
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used: int  # 单位：字节
    memory_available: int  # 单位：字节
    disk_io_read: int  # 单位：字节
    disk_io_write: int  # 单位：字节
    network_io_sent: int  # 单位：字节
    network_io_recv: int  # 单位：字节
    active_processes: int
    load_average: Optional[float] = None  # Linux系统负载


class PerformanceMonitor:
    """
    性能监控器
    
    负责实时监控系统性能指标，提供历史数据查询和阈值告警功能
    """
    
    def __init__(self, 
                 monitor_interval: int = 60,
                 max_history_hours: int = 24,
                 cpu_threshold: float = 80.0,
                 memory_threshold: float = 85.0):
        """
        初始化性能监控器
        
        Args:
            monitor_interval: 监控间隔，单位秒
            max_history_hours: 最大历史数据保存时间，单位小时
            cpu_threshold: CPU使用率告警阈值，百分比
            memory_threshold: 内存使用率告警阈值，百分比
        """
        self.monitor_interval = monitor_interval
        self.max_history_hours = max_history_hours
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        
        self.metrics_history: List[PerformanceMetrics] = []
        self.alert_callbacks: List[Callable[[str, Dict], None]] = []
        
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self.logger = logging.getLogger(__name__)
        
        # 初始化基线值
        self._last_disk_io = None
        self._last_network_io = None
        
    def start_monitoring(self):
        """开始性能监控"""
        if self._monitoring:
            self.logger.warning("性能监控已在运行中")
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("性能监控已启动")
        
    def stop_monitoring(self):
        """停止性能监控"""
        if not self._monitoring:
            self.logger.warning("性能监控未在运行")
            return
            
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        self.logger.info("性能监控已停止")
        
    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """
        添加告警回调函数
        
        Args:
            callback: 告警回调函数，参数为(alert_type, metrics_dict)
        """
        self.alert_callbacks.append(callback)
        
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存信息
            memory = psutil.virtual_memory()
            
            # 磁盘I/O
            disk_io = psutil.disk_io_counters()
            if self._last_disk_io:
                disk_read = disk_io.read_bytes - self._last_disk_io.read_bytes
                disk_write = disk_io.write_bytes - self._last_disk_io.write_bytes
            else:
                disk_read = disk_write = 0
            self._last_disk_io = disk_io
            
            # 网络I/O
            network_io = psutil.net_io_counters()
            if self._last_network_io:
                network_sent = network_io.bytes_sent - self._last_network_io.bytes_sent
                network_recv = network_io.bytes_recv - self._last_network_io.bytes_recv
            else:
                network_sent = network_recv = 0
            self._last_network_io = network_io
            
            # 进程数量
            active_processes = len(psutil.pids())
            
            # 系统负载（仅Linux）
            load_average = None
            try:
                if hasattr(psutil, 'getloadavg'):
                    load_average = psutil.getloadavg()[0]
            except (AttributeError, OSError):
                pass
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_available=memory.available,
                disk_io_read=disk_read,
                disk_io_write=disk_write,
                network_io_sent=network_sent,
                network_io_recv=network_recv,
                active_processes=active_processes,
                load_average=load_average
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"获取性能指标时发生错误: {e}")
            raise
            
    def get_metrics_history(self, hours: int = 1) -> List[PerformanceMetrics]:
        """
        获取历史性能指标
        
        Args:
            hours: 获取最近几小时的数据
            
        Returns:
            性能指标列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                metrics for metrics in self.metrics_history
                if metrics.timestamp >= cutoff_time
            ]
            
    def get_performance_summary(self, hours: int = 1) -> Dict:
        """
        获取性能摘要统计
        
        Args:
            hours: 统计最近几小时的数据
            
        Returns:
            性能摘要字典
        """
        history = self.get_metrics_history(hours)
        
        if not history:
            return {
                'period_hours': hours,
                'data_points': 0,
                'message': '无历史数据'
            }
            
        cpu_values = [m.cpu_percent for m in history]
        memory_values = [m.memory_percent for m in history]
        
        summary = {
            'period_hours': hours,
            'data_points': len(history),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'latest_metrics': {
                'cpu_percent': history[-1].cpu_percent,
                'memory_percent': history[-1].memory_percent,
                'memory_used_gb': round(history[-1].memory_used / (1024**3), 2),
                'active_processes': history[-1].active_processes
            }
        }
        
        return summary
        
    def check_alerts(self, metrics: PerformanceMetrics):
        """
        检查告警条件
        
        Args:
            metrics: 性能指标
        """
        alerts = []
        
        # CPU告警
        if metrics.cpu_percent > self.cpu_threshold:
            alerts.append({
                'type': 'cpu_high',
                'message': f'CPU使用率过高: {metrics.cpu_percent:.1f}%',
                'threshold': self.cpu_threshold,
                'current_value': metrics.cpu_percent
            })
            
        # 内存告警
        if metrics.memory_percent > self.memory_threshold:
            alerts.append({
                'type': 'memory_high',
                'message': f'内存使用率过高: {metrics.memory_percent:.1f}%',
                'threshold': self.memory_threshold,
                'current_value': metrics.memory_percent
            })
            
        # 发送告警
        for alert in alerts:
            self.logger.warning(f"性能告警: {alert['message']}")
            for callback in self.alert_callbacks:
                try:
                    callback(alert['type'], alert)
                except Exception as e:
                    self.logger.error(f"告警回调执行失败: {e}")
                    
    def _monitor_loop(self):
        """监控循环"""
        self.logger.info("性能监控循环已启动")
        
        while self._monitoring:
            try:
                # 获取当前指标
                metrics = self.get_current_metrics()
                
                # 保存到历史记录
                with self._lock:
                    self.metrics_history.append(metrics)
                    
                    # 清理过期数据
                    cutoff_time = datetime.now() - timedelta(hours=self.max_history_hours)
                    self.metrics_history = [
                        m for m in self.metrics_history
                        if m.timestamp >= cutoff_time
                    ]
                
                # 检查告警
                self.check_alerts(metrics)
                
                self.logger.debug(
                    f"性能监控 - CPU: {metrics.cpu_percent:.1f}%, "
                    f"内存: {metrics.memory_percent:.1f}%, "
                    f"进程数: {metrics.active_processes}"
                )
                
            except Exception as e:
                self.logger.error(f"性能监控循环中发生错误: {e}")
                
            # 等待下次监控
            time.sleep(self.monitor_interval)
            
    def is_monitoring(self) -> bool:
        """检查是否正在监控"""
        return self._monitoring
        
    def get_system_info(self) -> Dict:
        """获取系统基本信息"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            info = {
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'disk_usage': {},
                'system_uptime': str(datetime.now() - boot_time),
                'boot_time': boot_time.isoformat()
            }
            
            # 磁盘使用情况
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    info['disk_usage'][partition.mountpoint] = {
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 1)
                    }
                except PermissionError:
                    continue
                    
            return info
            
        except Exception as e:
            self.logger.error(f"获取系统信息时发生错误: {e}")
            return {}
            
    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        
        with self._lock:
            self.metrics_history.clear()
            self.alert_callbacks.clear()
            
        self.logger.info("性能监控器已清理") 