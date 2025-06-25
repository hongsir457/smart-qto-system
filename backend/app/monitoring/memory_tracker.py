"""
内存追踪器模块

负责追踪应用程序内存使用情况，检测内存泄露，监控对象生命周期
"""

import gc
import sys
import tracemalloc
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import weakref
import psutil
import os


@dataclass
class MemorySnapshot:
    """内存快照数据类"""
    timestamp: datetime
    total_memory: int  # 总内存，字节
    available_memory: int  # 可用内存，字节
    process_memory: int  # 进程内存，字节
    python_memory: int  # Python堆内存，字节
    object_counts: Dict[str, int] = field(default_factory=dict)  # 对象计数
    top_memory_blocks: List[Tuple[str, int]] = field(default_factory=list)  # 最大内存块


@dataclass
class ObjectTracker:
    """对象追踪器"""
    obj_type: str
    creation_time: datetime
    size_bytes: int
    traceback: Optional[List[str]] = None


class MemoryTracker:
    """
    内存追踪器
    
    负责监控Python进程的内存使用情况，追踪对象创建和销毁，检测潜在的内存泄露
    """
    
    def __init__(self, 
                 track_objects: bool = True,
                 max_snapshots: int = 100,
                 snapshot_interval: int = 300):  # 5分钟
        """
        初始化内存追踪器
        
        Args:
            track_objects: 是否追踪对象创建
            max_snapshots: 最大快照数量
            snapshot_interval: 快照间隔，单位秒
        """
        self.track_objects = track_objects
        self.max_snapshots = max_snapshots
        self.snapshot_interval = snapshot_interval
        
        self.snapshots: List[MemorySnapshot] = []
        self.tracked_objects: Dict[int, ObjectTracker] = {}
        self.object_refs = weakref.WeakSet()
        
        self._tracking = False
        self._track_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self.logger = logging.getLogger(__name__)
        
        # 启动tracemalloc
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            
        self.process = psutil.Process(os.getpid())
        
    def start_tracking(self):
        """开始内存追踪"""
        if self._tracking:
            self.logger.warning("内存追踪已在运行中")
            return
            
        self._tracking = True
        self._track_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._track_thread.start()
        self.logger.info("内存追踪已启动")
        
    def stop_tracking(self):
        """停止内存追踪"""
        if not self._tracking:
            self.logger.warning("内存追踪未在运行")
            return
            
        self._tracking = False
        if self._track_thread and self._track_thread.is_alive():
            self._track_thread.join(timeout=5)
        self.logger.info("内存追踪已停止")
        
    def take_snapshot(self) -> MemorySnapshot:
        """获取内存快照"""
        try:
            # 系统内存信息
            system_memory = psutil.virtual_memory()
            
            # 进程内存信息
            process_memory = self.process.memory_info()
            
            # Python内存信息
            python_memory = 0
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                python_memory = current
            
            # 对象计数
            object_counts = self._get_object_counts()
            
            # 最大内存块
            top_memory_blocks = self._get_top_memory_blocks()
            
            snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                total_memory=system_memory.total,
                available_memory=system_memory.available,
                process_memory=process_memory.rss,
                python_memory=python_memory,
                object_counts=object_counts,
                top_memory_blocks=top_memory_blocks
            )
            
            with self._lock:
                self.snapshots.append(snapshot)
                
                # 限制快照数量
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots:]
                    
            return snapshot
            
        except Exception as e:
            self.logger.error(f"获取内存快照时发生错误: {e}")
            raise
            
    def track_object(self, obj: Any, obj_type: str = None):
        """
        追踪对象
        
        Args:
            obj: 要追踪的对象
            obj_type: 对象类型名称
        """
        if not self.track_objects:
            return
            
        try:
            obj_id = id(obj)
            if obj_type is None:
                obj_type = type(obj).__name__
                
            # 获取对象大小
            size_bytes = sys.getsizeof(obj)
            
            # 获取创建堆栈
            traceback_list = None
            if tracemalloc.is_tracing():
                try:
                    traceback_list = tracemalloc.get_object_traceback(obj)
                    if traceback_list:
                        traceback_list = traceback_list.format()
                except Exception:
                    pass
                    
            tracker = ObjectTracker(
                obj_type=obj_type,
                creation_time=datetime.now(),
                size_bytes=size_bytes,
                traceback=traceback_list
            )
            
            with self._lock:
                self.tracked_objects[obj_id] = tracker
                
            # 添加到弱引用集合
            try:
                self.object_refs.add(obj)
            except TypeError:
                # 某些对象不支持弱引用
                pass
                
        except Exception as e:
            self.logger.error(f"追踪对象时发生错误: {e}")
            
    def get_memory_usage(self) -> Dict:
        """获取当前内存使用情况"""
        try:
            # 系统内存
            system_memory = psutil.virtual_memory()
            
            # 进程内存
            process_memory = self.process.memory_info()
            
            # Python内存
            python_memory = 0
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                python_memory = current
                
            usage = {
                'system': {
                    'total_gb': round(system_memory.total / (1024**3), 2),
                    'available_gb': round(system_memory.available / (1024**3), 2),
                    'used_percent': system_memory.percent
                },
                'process': {
                    'rss_mb': round(process_memory.rss / (1024**2), 2),
                    'vms_mb': round(process_memory.vms / (1024**2), 2)
                },
                'python': {
                    'traced_mb': round(python_memory / (1024**2), 2) if python_memory else 0
                },
                'objects': {
                    'tracked_count': len(self.tracked_objects),
                    'weakref_count': len(self.object_refs)
                }
            }
            
            return usage
            
        except Exception as e:
            self.logger.error(f"获取内存使用情况时发生错误: {e}")
            return {}
            
    def analyze_memory_growth(self, hours: int = 1) -> Dict:
        """
        分析内存增长趋势
        
        Args:
            hours: 分析最近几小时的数据
            
        Returns:
            内存增长分析结果
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_snapshots = [
                s for s in self.snapshots
                if s.timestamp >= cutoff_time
            ]
            
        if len(recent_snapshots) < 2:
            return {
                'message': '数据不足，无法分析增长趋势',
                'snapshots_count': len(recent_snapshots)
            }
            
        first_snapshot = recent_snapshots[0]
        last_snapshot = recent_snapshots[-1]
        
        # 计算增长
        process_growth = last_snapshot.process_memory - first_snapshot.process_memory
        python_growth = last_snapshot.python_memory - first_snapshot.python_memory
        
        # 对象计数变化
        object_changes = {}
        for obj_type in set(first_snapshot.object_counts.keys()) | set(last_snapshot.object_counts.keys()):
            first_count = first_snapshot.object_counts.get(obj_type, 0)
            last_count = last_snapshot.object_counts.get(obj_type, 0)
            change = last_count - first_count
            if change != 0:
                object_changes[obj_type] = {
                    'first': first_count,
                    'last': last_count,
                    'change': change
                }
                
        analysis = {
            'period_hours': hours,
            'snapshots_analyzed': len(recent_snapshots),
            'memory_growth': {
                'process_mb': round(process_growth / (1024**2), 2),
                'python_mb': round(python_growth / (1024**2), 2)
            },
            'object_changes': object_changes,
            'potential_leaks': []
        }
        
        # 检测潜在内存泄露
        for obj_type, change_info in object_changes.items():
            if change_info['change'] > 100:  # 对象增长超过100个
                analysis['potential_leaks'].append({
                    'type': obj_type,
                    'growth': change_info['change'],
                    'current_count': change_info['last']
                })
                
        return analysis
        
    def detect_memory_leaks(self) -> List[Dict]:
        """检测潜在的内存泄露"""
        leaks = []
        
        try:
            # 强制垃圾回收
            collected = gc.collect()
            self.logger.debug(f"垃圾回收清理了 {collected} 个对象")
            
            # 检查循环引用
            if gc.garbage:
                leaks.append({
                    'type': 'circular_references',
                    'count': len(gc.garbage),
                    'description': '发现循环引用对象'
                })
                
            # 检查追踪对象
            with self._lock:
                current_time = datetime.now()
                long_lived_objects = {}
                
                for obj_id, tracker in self.tracked_objects.items():
                    age = current_time - tracker.creation_time
                    if age.total_seconds() > 3600:  # 超过1小时的对象
                        obj_type = tracker.obj_type
                        if obj_type not in long_lived_objects:
                            long_lived_objects[obj_type] = []
                        long_lived_objects[obj_type].append({
                            'id': obj_id,
                            'age_hours': round(age.total_seconds() / 3600, 2),
                            'size_kb': round(tracker.size_bytes / 1024, 2)
                        })
                        
                for obj_type, objects in long_lived_objects.items():
                    if len(objects) > 10:  # 同类型长期存活对象过多
                        leaks.append({
                            'type': 'long_lived_objects',
                            'object_type': obj_type,
                            'count': len(objects),
                            'total_size_mb': round(sum(obj['size_kb'] for obj in objects) / 1024, 2),
                            'description': f'发现大量长期存活的{obj_type}对象'
                        })
                        
        except Exception as e:
            self.logger.error(f"检测内存泄露时发生错误: {e}")
            
        return leaks
        
    def get_top_memory_consumers(self, top_n: int = 10) -> List[Dict]:
        """
        获取内存消耗最大的对象类型
        
        Args:
            top_n: 返回前N个消耗最多的类型
            
        Returns:
            内存消耗排行榜
        """
        try:
            # 按类型统计内存使用
            type_memory = {}
            type_counts = {}
            
            with self._lock:
                for tracker in self.tracked_objects.values():
                    obj_type = tracker.obj_type
                    if obj_type not in type_memory:
                        type_memory[obj_type] = 0
                        type_counts[obj_type] = 0
                    type_memory[obj_type] += tracker.size_bytes
                    type_counts[obj_type] += 1
                    
            # 排序
            sorted_types = sorted(
                type_memory.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            
            consumers = []
            for obj_type, total_memory in sorted_types:
                consumers.append({
                    'type': obj_type,
                    'total_memory_mb': round(total_memory / (1024**2), 2),
                    'object_count': type_counts[obj_type],
                    'avg_size_kb': round(total_memory / type_counts[obj_type] / 1024, 2)
                })
                
            return consumers
            
        except Exception as e:
            self.logger.error(f"获取内存消耗排行时发生错误: {e}")
            return []
            
    def _get_object_counts(self) -> Dict[str, int]:
        """获取对象计数"""
        try:
            # 强制垃圾回收以获得准确计数
            gc.collect()
            
            # 统计对象计数
            object_counts = {}
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
                
            return object_counts
            
        except Exception as e:
            self.logger.error(f"获取对象计数时发生错误: {e}")
            return {}
            
    def _get_top_memory_blocks(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """获取最大内存块"""
        try:
            if not tracemalloc.is_tracing():
                return []
                
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')[:top_n]
            
            blocks = []
            for stat in top_stats:
                blocks.append((str(stat.traceback), stat.size))
                
            return blocks
            
        except Exception as e:
            self.logger.error(f"获取最大内存块时发生错误: {e}")
            return []
            
    def _tracking_loop(self):
        """追踪循环"""
        self.logger.info("内存追踪循环已启动")
        
        while self._tracking:
            try:
                # 获取内存快照
                snapshot = self.take_snapshot()
                
                self.logger.debug(
                    f"内存快照 - 进程: {round(snapshot.process_memory / (1024**2), 1)}MB, "
                    f"Python: {round(snapshot.python_memory / (1024**2), 1)}MB, "
                    f"追踪对象: {len(self.tracked_objects)}"
                )
                
                # 清理无效的追踪对象
                self._cleanup_tracked_objects()
                
            except Exception as e:
                self.logger.error(f"内存追踪循环中发生错误: {e}")
                
            # 等待下次追踪
            import time
            time.sleep(self.snapshot_interval)
            
    def _cleanup_tracked_objects(self):
        """清理无效的追踪对象"""
        try:
            with self._lock:
                # 查找已被垃圾回收的对象
                to_remove = []
                for obj_id in self.tracked_objects.keys():
                    # 这里无法直接检查对象是否存在，依赖弱引用集合
                    pass
                    
                # 移除过期对象（例如，超过24小时的对象）
                cutoff_time = datetime.now() - timedelta(hours=24)
                to_remove = [
                    obj_id for obj_id, tracker in self.tracked_objects.items()
                    if tracker.creation_time < cutoff_time
                ]
                
                for obj_id in to_remove:
                    del self.tracked_objects[obj_id]
                    
                if to_remove:
                    self.logger.debug(f"清理了 {len(to_remove)} 个过期追踪对象")
                    
        except Exception as e:
            self.logger.error(f"清理追踪对象时发生错误: {e}")
            
    def is_tracking(self) -> bool:
        """检查是否正在追踪"""
        return self._tracking
        
    def get_snapshots_summary(self) -> Dict:
        """获取快照摘要"""
        with self._lock:
            if not self.snapshots:
                return {'message': '暂无快照数据'}
                
            latest = self.snapshots[-1]
            first = self.snapshots[0]
            
            summary = {
                'snapshots_count': len(self.snapshots),
                'time_span_hours': round(
                    (latest.timestamp - first.timestamp).total_seconds() / 3600, 2
                ),
                'latest_snapshot': {
                    'timestamp': latest.timestamp.isoformat(),
                    'process_memory_mb': round(latest.process_memory / (1024**2), 2),
                    'python_memory_mb': round(latest.python_memory / (1024**2), 2)
                },
                'memory_trend': {
                    'process_change_mb': round(
                        (latest.process_memory - first.process_memory) / (1024**2), 2
                    ),
                    'python_change_mb': round(
                        (latest.python_memory - first.python_memory) / (1024**2), 2
                    )
                }
            }
            
            return summary
            
    def cleanup(self):
        """清理资源"""
        self.stop_tracking()
        
        with self._lock:
            self.snapshots.clear()
            self.tracked_objects.clear()
            
        # 停止tracemalloc（可选）
        # tracemalloc.stop()
        
        self.logger.info("内存追踪器已清理") 