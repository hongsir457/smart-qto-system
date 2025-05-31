from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart QTO System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 基础路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODEL_PATH: Path = BASE_DIR / "app" / "models"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    EXPORT_DIR: Path = BASE_DIR / "exports"
    
    # 数据库配置
    POSTGRES_SERVER: str = "dbconn.sealoshzh.site:48982"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "2xn59xgm"
    POSTGRES_DB: str = "postgres"  # 如有自定义数据库名请改成你的库名
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".dwg", ".dxf"}

    # AI模型配置
    CONFIDENCE_THRESHOLD: float = 0.5
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
    
    # OpenAI API配置
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_DEFAULT_MODEL: str = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-2024-11-20")

    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2

    # S3配置
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = ""
    
    # Windows Celery配置
    CELERY_BROKER_POOL_LIMIT: int = 1
    CELERY_BROKER_CONNECTION_TIMEOUT: int = 30
    CELERY_BROKER_CONNECTION_RETRY: bool = True
    CELERY_BROKER_CONNECTION_MAX_RETRIES: int = 3
    CELERY_TASK_SERIALIZER: str = 'json'
    CELERY_RESULT_SERIALIZER: str = 'json'
    CELERY_ACCEPT_CONTENT: list = ['json']
    CELERY_TASK_RESULT_EXPIRES: int = 3600
    CELERY_WORKER_CONCURRENCY: int = 1
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = 1
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    BROKER_CONNECTION_RETRY_ON_STARTUP: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.MODEL_PATH, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True) 