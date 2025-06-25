import os
from celery import Celery, signals
from app.core.config import settings
import socket
from kombu import Queue, Exchange

# Windows平台特定设置
if os.name == 'nt':
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

# 生成唯一的节点名称
hostname = socket.gethostname()
worker_name = f"worker_{hostname}_{os.getpid()}"

# 定义默认队列和交换机
default_exchange = Exchange('default', type='direct')
default_queue = Queue('default', default_exchange, routing_key='default')

# 创建中心化的Celery实例
celery_app = Celery(
    "smart_qto_system",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.tasks.drawing_tasks',
        'app.tasks.ocr_tasks', 
        'app.tasks.analysis_tasks'
    ]
)

# 配置Celery
celery_app.conf.update(
    # 任务序列化
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    task_result_expires=settings.CELERY_TASK_RESULT_EXPIRES,
    
    # Worker配置
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_send_task_events=True,
    worker_pool_restarts=True,
    
    # Broker配置
    broker_pool_limit=settings.CELERY_BROKER_POOL_LIMIT,
    broker_connection_timeout=settings.CELERY_BROKER_CONNECTION_TIMEOUT,
    broker_connection_retry=settings.CELERY_BROKER_CONNECTION_RETRY,
    broker_connection_max_retries=settings.CELERY_BROKER_CONNECTION_MAX_RETRIES,
    broker_connection_retry_on_startup=True,
    
    # 任务配置
    task_queues=(default_queue,),
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    task_track_started=True,
    task_time_limit=1800,  # 30分钟
    task_soft_time_limit=1500,  # 25分钟
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 时区配置
    timezone='Asia/Shanghai',
    enable_utc=False,
    
    # 结果后端配置
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0,
            'max_retries': 10,
            'interval_start': 0,
            'interval_step': 0.2,
            'interval_max': 0.5,
        }
    },
    
    # 任务路由配置
    task_routes={
        'app.tasks.ocr_tasks.*': {'queue': 'default'},
        'app.tasks.analysis_tasks.*': {'queue': 'default'},
        'app.tasks.drawing_tasks.*': {'queue': 'default'}
    }
)

# 自动发现任务
celery_app.autodiscover_tasks([
    'app.tasks.ocr_tasks', 
    'app.tasks.analysis_tasks',
    'app.tasks.drawing_tasks'
])

# 任务错误处理
@signals.task_failure.connect
def handle_task_failure(task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    print(f'Task {task_id} failed: {exception}')
    print(f'Args: {args}')
    print(f'Kwargs: {kwargs}')
    print(f'Traceback: {traceback}') 