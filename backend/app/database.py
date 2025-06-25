import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from sqlalchemy.pool import QueuePool
import time
import random

# 配置日志
logger = logging.getLogger(__name__)

# 数据库URL
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# 根据数据库类型设置不同的连接参数
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite配置
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},  # SQLite特有参数
        echo=False,
        future=True
    )
else:
    # PostgreSQL配置
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "prefer",
            "connect_timeout": 30,
            "application_name": "smart_qto_system",
            "keepalives_idle": 600,
            "keepalives_interval": 30,
            "keepalives_count": 3,
        },
        echo=False,
        future=True
    )

# 添加连接事件监听器
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """设置连接参数"""
    logger.info("数据库连接建立")

@event.listens_for(engine, "close")
def receive_close(dbapi_connection, connection_record):
    """连接关闭事件"""
    logger.info("数据库连接关闭")

@event.listens_for(engine, "invalidate")
def receive_invalidate(dbapi_connection, connection_record, exception):
    """连接失效事件"""
    logger.warning(f"数据库连接失效: {exception}")

# 创建会话工厂，优化会话配置
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False     # 避免commit后对象过期导致的查询
)

Base = declarative_base()

# 依赖项
def get_db():
    """获取数据库会话的依赖项"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 重连装饰器
def with_db_retry(max_retries=3, delay=1):
    """数据库操作重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (SQLAlchemyError, DisconnectionError) as e:
                    last_exception = e
                    logger.warning(f"数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # 指数退避
                        # 重新创建会话
                        if 'db' in kwargs:
                            kwargs['db'].close()
                            kwargs['db'] = SessionLocal()
                        continue
                    else:
                        logger.error(f"数据库操作最终失败: {e}")
                        raise last_exception
            return None
        return wrapper
    return decorator

# 安全的数据库会话管理器
class SafeDBSession:
    """安全的数据库会话管理器，自动处理连接问题"""
    
    def __init__(self):
        self.session = None
    
    def __enter__(self):
        self.session = SessionLocal()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                if exc_type:
                    self.session.rollback()
                else:
                    self.session.commit()
            except Exception as e:
                logger.error(f"会话提交/回滚失败: {e}")
                self.session.rollback()
            finally:
                self.session.close()
    
    def safe_commit(self):
        """安全提交，自动处理异常"""
        try:
            self.session.commit()
            return True
        except (SQLAlchemyError, DisconnectionError) as e:
            logger.warning(f"提交失败，尝试重连: {e}")
            self.session.rollback()
            # 重新创建会话
            self.session.close()
            self.session = SessionLocal()
            return False
        except Exception as e:
            logger.error(f"提交失败: {e}")
            self.session.rollback()
            return False

# 用于Celery任务的数据库会话管理
def get_celery_db_session():
    """为Celery任务获取数据库会话"""
    return SafeDBSession()

# 检查数据库连接
def check_db_connection():
    """检查数据库连接状态"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("数据库连接正常")
        return True
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False

# 清理连接池
def cleanup_db_connections():
    """清理数据库连接池"""
    try:
        engine.dispose()
        logger.info("数据库连接池已清理")
    except Exception as e:
        logger.error(f"清理连接池失败: {e}") 