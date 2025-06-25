"""
Celery优化配置 - 防止任务丢失和提高稳定性
"""

from app.core.config import settings

# Celery优化配置
CELERY_CONFIG = {
    # 基础配置
    'broker_url': settings.CELERY_BROKER_URL,
    'result_backend': settings.CELERY_RESULT_BACKEND,
    
    # 🔧 任务确认和可靠性配置
    'task_acks_late': True,  # 任务完成后才确认，防止任务丢失
    'worker_prefetch_multiplier': 1,  # 一次只取一个任务，避免任务堆积
    'task_reject_on_worker_lost': True,  # worker丢失时拒绝任务
    
    # 🔧 任务重试配置
    'task_default_retry_delay': 60,  # 默认重试延迟60秒
    'task_max_retries': 3,  # 最大重试3次
    'task_retry_jitter': True,  # 添加随机延迟避免雪崩
    
    # 🔧 结果存储配置
    'result_expires': 7200,  # 结果保存2小时
    'result_persistent': True,  # 持久化结果
    'result_compression': 'gzip',  # 压缩结果
    
    # 🔧 序列化配置
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    
    # 🔧 连接配置
    'broker_connection_retry_on_startup': True,
    'broker_connection_retry': True,
    'broker_connection_max_retries': 10,
    'broker_heartbeat': 30,
    'broker_pool_limit': 10,
    
    # 🔧 Worker配置
    'worker_concurrency': 1,  # Windows环境建议单进程
    'worker_max_tasks_per_child': 10,  # 每个worker最多处理10个任务后重启
    'worker_disable_rate_limits': True,
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    
    # 🔧 监控配置
    'worker_log_format': '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    'worker_task_log_format': '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # 🔧 任务路由配置
    'task_routes': {
        'app.tasks.*': {'queue': 'default'},
        'app.tasks.drawing_analysis_task': {'queue': 'analysis'},
        'app.tasks.heavy_analysis_task': {'queue': 'heavy'},
    },
    
    # 🔧 队列配置
    'task_default_queue': 'default',
    'task_default_exchange': 'default',
    'task_default_exchange_type': 'direct',
    'task_default_routing_key': 'default',
    
    # 🔧 任务限制
    'task_soft_time_limit': 1800,  # 软限制30分钟
    'task_time_limit': 2400,  # 硬限制40分钟
    'worker_max_memory_per_child': 200000,  # 200MB内存限制
    
    # 🔧 错误处理
    'task_ignore_result': False,  # 不忽略结果
    'task_store_errors_even_if_ignored': True,  # 即使忽略也存储错误
    
    # 🔧 安全配置
    'worker_hijack_root_logger': False,
    'worker_log_color': False,
    
    # 🔧 性能优化
    'task_compression': 'gzip',
    'result_backend_transport_options': {
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # 🔧 Windows特定配置
    'worker_pool': 'solo',  # Windows使用solo pool
    'broker_transport_options': {
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
    }
}

# 任务注解配置
TASK_ANNOTATIONS = {
    '*': {
        'rate_limit': '10/s',
        'time_limit': 2400,
        'soft_time_limit': 1800,
    },
    'app.tasks.drawing_analysis_task': {
        'rate_limit': '2/s',  # 分析任务限制更严格
        'time_limit': 3600,
        'soft_time_limit': 3000,
        'retry_policy': {
            'max_retries': 3,
            'interval_start': 0,
            'interval_step': 60,
            'interval_max': 300,
        }
    },
    'app.tasks.heavy_analysis_task': {
        'rate_limit': '1/s',  # 重型任务最严格
        'time_limit': 7200,
        'soft_time_limit': 6600,
        'retry_policy': {
            'max_retries': 2,
            'interval_start': 0,
            'interval_step': 120,
            'interval_max': 600,
        }
    }
}

# 将注解添加到配置中
CELERY_CONFIG['task_annotations'] = TASK_ANNOTATIONS 