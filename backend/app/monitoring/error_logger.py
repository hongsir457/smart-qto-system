"""
错误日志记录器模块

负责错误日志的收集、分类、分析和报告
"""

import logging
import traceback
import sys
import threading
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import inspect
import os


class ErrorLevel(Enum):
    """错误级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误分类枚举"""
    SYSTEM = "system"          # 系统错误
    DATABASE = "database"      # 数据库错误
    NETWORK = "network"        # 网络错误
    VALIDATION = "validation"  # 验证错误
    BUSINESS = "business"      # 业务逻辑错误
    SECURITY = "security"      # 安全错误
    PERFORMANCE = "performance" # 性能问题
    UNKNOWN = "unknown"        # 未知错误


@dataclass
class ErrorRecord:
    """错误记录数据类"""
    error_id: str
    timestamp: datetime
    level: ErrorLevel
    category: ErrorCategory
    message: str
    exception_type: Optional[str] = None
    traceback: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    user_id: Optional[int] = None
    request_id: Optional[str] = None
    task_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    count: int = 1  # 相同错误的出现次数
    first_occurrence: Optional[datetime] = None
    last_occurrence: Optional[datetime] = None


@dataclass
class ErrorSummary:
    """错误摘要数据类"""
    total_errors: int
    error_rate: float
    top_errors: List[Dict[str, Any]]
    errors_by_category: Dict[str, int]
    errors_by_level: Dict[str, int]
    trend_data: Dict[str, List[int]]
    critical_errors: int
    new_errors: int


class ErrorLogger:
    """
    错误日志记录器
    
    负责收集、分类、分析和报告应用程序中的错误
    """
    
    def __init__(self, 
                 max_error_records: int = 50000,
                 dedup_window_hours: int = 24,
                 cleanup_interval: int = 3600):
        """
        初始化错误日志记录器
        
        Args:
            max_error_records: 最大错误记录数量
            dedup_window_hours: 重复错误去重时间窗口，小时
            cleanup_interval: 清理间隔，秒
        """
        self.max_error_records = max_error_records
        self.dedup_window_hours = dedup_window_hours
        self.cleanup_interval = cleanup_interval
        
        self.error_records: Dict[str, ErrorRecord] = {}
        self.error_history: deque = deque(maxlen=max_error_records)
        self.error_index: Dict[str, str] = {}  # 错误签名 -> 错误ID
        
        # 统计计数器
        self.error_counters = defaultdict(int)
        self.category_counters = defaultdict(int)
        self.level_counters = defaultdict(int)
        self.hourly_counters = defaultdict(int)
        
        # 监控状态
        self._monitoring = False
        self._cleanup_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 告警配置
        self.alert_callbacks: List[Callable[[str, Dict], None]] = []
        self.alert_thresholds = {
            'critical_errors_per_hour': 10,
            'error_rate_percent': 5.0,
            'new_error_types': 5
        }
        
        self.logger = logging.getLogger(__name__)
        
        # 设置自定义异常处理器
        self._setup_exception_handler()
        
    def start_monitoring(self):
        """开始错误监控"""
        if self._monitoring:
            self.logger.warning("错误监控已在运行中")
            return
            
        self._monitoring = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        self.logger.info("错误监控已启动")
        
    def stop_monitoring(self):
        """停止错误监控"""
        if not self._monitoring:
            self.logger.warning("错误监控未在运行")
            return
            
        self._monitoring = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        self.logger.info("错误监控已停止")
        
    def log_error(self, 
                  message: str,
                  level: ErrorLevel = ErrorLevel.ERROR,
                  category: ErrorCategory = ErrorCategory.UNKNOWN,
                  exception: Optional[Exception] = None,
                  user_id: Optional[int] = None,
                  request_id: Optional[str] = None,
                  task_id: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None) -> str:
        """
        记录错误
        
        Args:
            message: 错误消息
            level: 错误级别
            category: 错误分类
            exception: 异常对象
            user_id: 用户ID
            request_id: 请求ID
            task_id: 任务ID
            context: 上下文信息
            
        Returns:
            错误ID
        """
        try:
            # 获取调用栈信息
            frame = inspect.currentframe().f_back
            module = frame.f_globals.get('__name__', 'unknown')
            function = frame.f_code.co_name
            line_number = frame.f_lineno
            
            # 处理异常信息
            exception_type = None
            traceback_str = None
            if exception:
                exception_type = type(exception).__name__
                traceback_str = ''.join(traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                ))
            elif level in [ErrorLevel.ERROR, ErrorLevel.CRITICAL]:
                # 自动获取当前异常
                exc_info = sys.exc_info()
                if exc_info[0] is not None:
                    exception_type = exc_info[0].__name__
                    traceback_str = ''.join(traceback.format_exception(*exc_info))
                    
            # 生成错误签名用于去重
            error_signature = self._generate_error_signature(
                message, exception_type, module, function, line_number
            )
            
            current_time = datetime.now()
            
            with self._lock:
                # 检查是否是重复错误
                if error_signature in self.error_index:
                    error_id = self.error_index[error_signature]
                    existing_error = self.error_records[error_id]
                    
                    # 更新重复错误计数
                    existing_error.count += 1
                    existing_error.last_occurrence = current_time
                    
                    # 更新上下文信息
                    if context:
                        existing_error.context.update(context)
                        
                    self.logger.debug(f"重复错误更新: {error_id} (计数: {existing_error.count})")
                    return error_id
                    
                # 创建新的错误记录
                error_id = self._generate_error_id()
                
                error_record = ErrorRecord(
                    error_id=error_id,
                    timestamp=current_time,
                    level=level,
                    category=category,
                    message=message,
                    exception_type=exception_type,
                    traceback=traceback_str,
                    module=module,
                    function=function,
                    line_number=line_number,
                    user_id=user_id,
                    request_id=request_id,
                    task_id=task_id,
                    context=context or {},
                    first_occurrence=current_time,
                    last_occurrence=current_time
                )
                
                # 保存错误记录
                self.error_records[error_id] = error_record
                self.error_history.append(error_record)
                self.error_index[error_signature] = error_id
                
                # 更新统计计数器
                self.error_counters['total'] += 1
                self.category_counters[category.value] += 1
                self.level_counters[level.value] += 1
                self.hourly_counters[current_time.hour] += 1
                
                if level == ErrorLevel.CRITICAL:
                    self.error_counters['critical'] += 1
                    
            # 记录到标准日志
            log_level = getattr(logging, level.value.upper())
            self.logger.log(log_level, f"[{error_id}] {message}", extra={
                'error_id': error_id,
                'category': category.value,
                'exception_type': exception_type,
                'user_id': user_id,
                'request_id': request_id,
                'task_id': task_id
            })
            
            # 检查告警条件
            self._check_alerts(error_record)
            
            return error_id
            
        except Exception as e:
            # 防止错误记录器本身出错
            self.logger.error(f"错误记录器内部错误: {e}")
            return "error_logger_failure"
            
    def log_exception(self, 
                     exception: Exception,
                     category: ErrorCategory = ErrorCategory.UNKNOWN,
                     user_id: Optional[int] = None,
                     request_id: Optional[str] = None,
                     task_id: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None) -> str:
        """
        记录异常
        
        Args:
            exception: 异常对象
            category: 错误分类
            user_id: 用户ID
            request_id: 请求ID
            task_id: 任务ID
            context: 上下文信息
            
        Returns:
            错误ID
        """
        return self.log_error(
            message=str(exception),
            level=ErrorLevel.ERROR,
            category=category,
            exception=exception,
            user_id=user_id,
            request_id=request_id,
            task_id=task_id,
            context=context
        )
        
    def get_error_summary(self, hours: int = 24) -> ErrorSummary:
        """
        获取错误摘要
        
        Args:
            hours: 统计时间范围，小时
            
        Returns:
            错误摘要
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            # 筛选时间范围内的错误
            recent_errors = [
                error for error in self.error_history
                if error.timestamp >= cutoff_time
            ]
            
            total_errors = len(recent_errors)
            
            # 按分类统计
            errors_by_category = defaultdict(int)
            errors_by_level = defaultdict(int)
            
            for error in recent_errors:
                errors_by_category[error.category.value] += error.count
                errors_by_level[error.level.value] += error.count
                
            # 统计关键错误
            critical_errors = sum(
                error.count for error in recent_errors
                if error.level == ErrorLevel.CRITICAL
            )
            
            # 查找新错误（首次出现在时间范围内）
            new_errors = len([
                error for error in recent_errors
                if error.first_occurrence >= cutoff_time
            ])
            
            # 获取热门错误
            error_counts = {}
            for error in recent_errors:
                key = f"{error.message[:100]}..."
                error_counts[key] = error_counts.get(key, 0) + error.count
                
            top_errors = [
                {'message': msg, 'count': count}
                for msg, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # 生成趋势数据（按小时）
            trend_data = defaultdict(list)
            for i in range(hours):
                hour_start = datetime.now() - timedelta(hours=i+1)
                hour_end = datetime.now() - timedelta(hours=i)
                
                hour_errors = [
                    error for error in recent_errors
                    if hour_start <= error.timestamp < hour_end
                ]
                
                trend_data['errors'].append(len(hour_errors))
                trend_data['critical'].append(len([
                    error for error in hour_errors
                    if error.level == ErrorLevel.CRITICAL
                ]))
                
            # 计算错误率（假设有总请求数，这里简化处理）
            error_rate = (total_errors / max(1, hours * 100)) * 100  # 假设每小时100请求
            
            return ErrorSummary(
                total_errors=total_errors,
                error_rate=error_rate,
                top_errors=top_errors,
                errors_by_category=dict(errors_by_category),
                errors_by_level=dict(errors_by_level),
                trend_data=dict(trend_data),
                critical_errors=critical_errors,
                new_errors=new_errors
            )
            
    def get_error_details(self, error_id: str) -> Optional[ErrorRecord]:
        """
        获取错误详情
        
        Args:
            error_id: 错误ID
            
        Returns:
            错误记录，如果不存在返回None
        """
        with self._lock:
            return self.error_records.get(error_id)
            
    def search_errors(self, 
                     category: Optional[ErrorCategory] = None,
                     level: Optional[ErrorLevel] = None,
                     user_id: Optional[int] = None,
                     hours: int = 24,
                     limit: int = 100) -> List[ErrorRecord]:
        """
        搜索错误记录
        
        Args:
            category: 错误分类筛选
            level: 错误级别筛选
            user_id: 用户ID筛选
            hours: 时间范围，小时
            limit: 返回结果限制
            
        Returns:
            匹配的错误记录列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            filtered_errors = []
            
            for error in self.error_history:
                if error.timestamp < cutoff_time:
                    continue
                    
                if category and error.category != category:
                    continue
                    
                if level and error.level != level:
                    continue
                    
                if user_id and error.user_id != user_id:
                    continue
                    
                filtered_errors.append(error)
                
                if len(filtered_errors) >= limit:
                    break
                    
            return filtered_errors
            
    def get_error_trends(self, hours: int = 24) -> Dict[str, List]:
        """
        获取错误趋势数据
        
        Args:
            hours: 时间范围，小时
            
        Returns:
            趋势数据
        """
        hourly_data = defaultdict(lambda: defaultdict(int))
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            for error in self.error_history:
                if error.timestamp < cutoff_time:
                    continue
                    
                hour_key = error.timestamp.strftime('%Y-%m-%d %H:00')
                hourly_data[hour_key]['total'] += error.count
                hourly_data[hour_key][error.level.value] += error.count
                hourly_data[hour_key][error.category.value] += error.count
                
        return dict(hourly_data)
        
    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """
        添加告警回调函数
        
        Args:
            callback: 告警回调函数
        """
        self.alert_callbacks.append(callback)
        
    def set_alert_threshold(self, threshold_name: str, value: float):
        """
        设置告警阈值
        
        Args:
            threshold_name: 阈值名称
            value: 阈值
        """
        if threshold_name in self.alert_thresholds:
            self.alert_thresholds[threshold_name] = value
            self.logger.info(f"更新告警阈值: {threshold_name} = {value}")
        else:
            self.logger.warning(f"未知的告警阈值: {threshold_name}")
            
    def export_errors(self, 
                     hours: int = 24,
                     format: str = 'json') -> str:
        """
        导出错误数据
        
        Args:
            hours: 时间范围，小时
            format: 导出格式 ('json', 'csv')
            
        Returns:
            导出的数据字符串
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                error for error in self.error_history
                if error.timestamp >= cutoff_time
            ]
            
        if format == 'json':
            error_data = []
            for error in recent_errors:
                error_data.append({
                    'error_id': error.error_id,
                    'timestamp': error.timestamp.isoformat(),
                    'level': error.level.value,
                    'category': error.category.value,
                    'message': error.message,
                    'exception_type': error.exception_type,
                    'module': error.module,
                    'function': error.function,
                    'line_number': error.line_number,
                    'user_id': error.user_id,
                    'request_id': error.request_id,
                    'task_id': error.task_id,
                    'count': error.count,
                    'context': error.context
                })
            return json.dumps(error_data, indent=2, ensure_ascii=False)
            
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入表头
            writer.writerow([
                'error_id', 'timestamp', 'level', 'category', 'message',
                'exception_type', 'module', 'function', 'line_number',
                'user_id', 'request_id', 'task_id', 'count'
            ])
            
            # 写入数据
            for error in recent_errors:
                writer.writerow([
                    error.error_id,
                    error.timestamp.isoformat(),
                    error.level.value,
                    error.category.value,
                    error.message,
                    error.exception_type,
                    error.module,
                    error.function,
                    error.line_number,
                    error.user_id,
                    error.request_id,
                    error.task_id,
                    error.count
                ])
                
            return output.getvalue()
            
        else:
            raise ValueError(f"不支持的导出格式: {format}")
            
    def _generate_error_signature(self, 
                                 message: str, 
                                 exception_type: Optional[str],
                                 module: str, 
                                 function: str, 
                                 line_number: int) -> str:
        """生成错误签名用于去重"""
        signature_data = f"{message}|{exception_type}|{module}|{function}|{line_number}"
        return hashlib.md5(signature_data.encode()).hexdigest()
        
    def _generate_error_id(self) -> str:
        """生成错误ID"""
        import uuid
        return f"err_{uuid.uuid4().hex[:8]}"
        
    def _check_alerts(self, error_record: ErrorRecord):
        """检查告警条件"""
        try:
            alerts = []
            
            # 关键错误告警
            if error_record.level == ErrorLevel.CRITICAL:
                # 检查最近一小时的关键错误数量
                recent_critical = self._count_recent_errors(
                    hours=1, 
                    level=ErrorLevel.CRITICAL
                )
                
                if recent_critical >= self.alert_thresholds['critical_errors_per_hour']:
                    alerts.append({
                        'type': 'critical_errors_threshold',
                        'message': f'关键错误过多: 最近1小时发生 {recent_critical} 次',
                        'count': recent_critical,
                        'threshold': self.alert_thresholds['critical_errors_per_hour']
                    })
                    
            # 新错误类型告警
            if error_record.first_occurrence == error_record.last_occurrence:
                recent_new_errors = self._count_new_errors(hours=1)
                
                if recent_new_errors >= self.alert_thresholds['new_error_types']:
                    alerts.append({
                        'type': 'new_error_types_threshold',
                        'message': f'新错误类型过多: 最近1小时出现 {recent_new_errors} 种新错误',
                        'count': recent_new_errors,
                        'threshold': self.alert_thresholds['new_error_types']
                    })
                    
            # 发送告警
            for alert in alerts:
                self.logger.warning(f"错误告警: {alert['message']}")
                
                for callback in self.alert_callbacks:
                    try:
                        callback(alert['type'], alert)
                    except Exception as e:
                        self.logger.error(f"告警回调执行失败: {e}")
                        
        except Exception as e:
            self.logger.error(f"检查错误告警时发生异常: {e}")
            
    def _count_recent_errors(self, 
                           hours: int, 
                           level: Optional[ErrorLevel] = None,
                           category: Optional[ErrorCategory] = None) -> int:
        """统计最近的错误数量"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        count = 0
        
        for error in self.error_history:
            if error.timestamp < cutoff_time:
                continue
                
            if level and error.level != level:
                continue
                
            if category and error.category != category:
                continue
                
            count += error.count
            
        return count
        
    def _count_new_errors(self, hours: int) -> int:
        """统计新错误类型数量"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return len([
            error for error in self.error_history
            if error.first_occurrence >= cutoff_time
        ])
        
    def _setup_exception_handler(self):
        """设置全局异常处理器"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
                
            self.log_error(
                message=f"未处理的异常: {str(exc_value)}",
                level=ErrorLevel.CRITICAL,
                category=ErrorCategory.SYSTEM,
                exception=exc_value
            )
            
        sys.excepthook = handle_exception
        
    def _cleanup_loop(self):
        """清理循环"""
        self.logger.info("错误日志清理循环已启动")
        
        while self._monitoring:
            try:
                self._cleanup_old_errors()
                
            except Exception as e:
                self.logger.error(f"错误日志清理循环中发生错误: {e}")
                
            import time
            time.sleep(self.cleanup_interval)
            
    def _cleanup_old_errors(self):
        """清理过期错误记录"""
        cutoff_time = datetime.now() - timedelta(hours=self.dedup_window_hours * 2)
        
        with self._lock:
            # 查找过期的错误记录
            expired_error_ids = []
            expired_signatures = []
            
            for error_id, error_record in self.error_records.items():
                if error_record.last_occurrence < cutoff_time:
                    expired_error_ids.append(error_id)
                    
            # 查找对应的签名
            for signature, error_id in list(self.error_index.items()):
                if error_id in expired_error_ids:
                    expired_signatures.append(signature)
                    
            # 删除过期记录
            for error_id in expired_error_ids:
                del self.error_records[error_id]
                
            for signature in expired_signatures:
                del self.error_index[signature]
                
            if expired_error_ids:
                self.logger.debug(f"清理了 {len(expired_error_ids)} 个过期错误记录")
                
    def is_monitoring(self) -> bool:
        """检查是否正在监控"""
        return self._monitoring
        
    def cleanup(self):
        """清理资源"""
        self.stop_monitoring()
        
        with self._lock:
            self.error_records.clear()
            self.error_history.clear()
            self.error_index.clear()
            self.error_counters.clear()
            self.category_counters.clear()
            self.level_counters.clear()
            self.hourly_counters.clear()
            self.alert_callbacks.clear()
            
        self.logger.info("错误日志记录器已清理") 