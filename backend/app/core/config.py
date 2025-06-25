from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator, Field
from typing import Optional, List, Any, Union
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "智能工程量清单系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = Field(False, env="DEBUG")  # 调试模式
    
    # 基础路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODEL_PATH: Path = BASE_DIR / "app" / "models"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    EXPORT_DIR: Path = BASE_DIR / "exports"
    
    # 数据库配置 - 使用绝对路径以确保稳定性
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app' / 'database.db'}")
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
    
    # Celery配置 - 默认使用Redis
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # WebSocket配置
    WEBSOCKET_URL: str = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws")
    
    # 跨域配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 文件上传配置
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # AI服务配置
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_API_URL: str = os.getenv("AI_API_URL", "")

    # 统一云存储配置 (Sealos S3) - 凭证已更新
    # 警告: 生产环境中建议将密钥存储在环境变量或密钥管理服务中
    S3_ENDPOINT: str = Field(os.getenv("S3_ENDPOINT", "https://objectstorageapi.hzh.sealos.run"), env="S3_ENDPOINT")
    S3_ACCESS_KEY: str = Field(os.getenv("S3_ACCESS_KEY", "gkg9z6uk"), env="S3_ACCESS_KEY")
    S3_SECRET_KEY: str = Field(os.getenv("S3_SECRET_KEY", "z445tvss8vb8rgwz"), env="S3_SECRET_KEY")
    S3_BUCKET_NAME: str = Field(os.getenv("S3_BUCKET_NAME", "gkg9z6uk-smaryqto"), env="S3_BUCKET_NAME")
    S3_REGION: str = Field(os.getenv("S3_REGION", "us-east-1"), env="S3_REGION")

    # 统一数据库配置 - 支持Sealos PostgreSQL
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql://postgres:2xn59xgm@dbconn.sealoshzh.site:48982/postgres")

    # JWT配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # AI模型配置
    CONFIDENCE_THRESHOLD: float = 0.5
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
    
    # OpenAI API配置
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field("gpt-4o-2024-11-20", env="OPENAI_MODEL")  # 使用指定的GPT-4o模型
    OPENAI_MAX_TOKENS: int = Field(4000, env="OPENAI_MAX_TOKENS")  # 增加token限制以支持复杂图纸分析
    OPENAI_TEMPERATURE: float = Field(0.1, env="OPENAI_TEMPERATURE")
    
    # OCR 配置
    TESSERACT_PATH: str = Field("", env="TESSERACT_PATH")  # Tesseract可执行文件路径
    OCR_LANGUAGES: str = Field("chi_sim+eng", env="OCR_LANGUAGES")  # OCR识别语言
    OCR_CONFIDENCE_THRESHOLD: int = Field(30, env="OCR_CONFIDENCE_THRESHOLD")  # OCR置信度阈值
    
    # PaddleOCR图像自动调整配置
    PADDLE_OCR_AUTO_RESIZE: bool = Field(True, env="PADDLE_OCR_AUTO_RESIZE")  # 是否启用自动resize
    PADDLE_OCR_TARGET_DPI: int = Field(300, env="PADDLE_OCR_TARGET_DPI")  # 目标DPI
    PADDLE_OCR_MIN_HEIGHT: int = Field(32, env="PADDLE_OCR_MIN_HEIGHT")  # 最小文字高度像素
    PADDLE_OCR_MAX_SIZE: int = Field(4096, env="PADDLE_OCR_MAX_SIZE")  # 最大边长限制
    PADDLE_OCR_SMART_SCALE: bool = Field(True, env="PADDLE_OCR_SMART_SCALE")  # 智能缩放
    PADDLE_OCR_CONTRAST_ENHANCE: bool = Field(True, env="PADDLE_OCR_CONTRAST_ENHANCE")  # 对比度增强
    PADDLE_OCR_NOISE_REDUCTION: bool = Field(True, env="PADDLE_OCR_NOISE_REDUCTION")  # 降噪处理
    
    # 图像处理配置
    MAX_IMAGE_SIZE: int = Field(0, env="MAX_IMAGE_SIZE")  # 图像尺寸无限制 (0=无限制，支持超高分辨率建筑图纸)
    IMAGE_QUALITY: int = Field(98, env="IMAGE_QUALITY")  # 图像质量 (提升到98%)
    
    # 工程量计算配置
    DEFAULT_COLUMN_HEIGHT: float = Field(3.6, env="DEFAULT_COLUMN_HEIGHT")  # 默认柱高（米）
    DEFAULT_BEAM_LENGTH: float = Field(6.0, env="DEFAULT_BEAM_LENGTH")  # 默认梁长（米）
    DEFAULT_SLAB_AREA: float = Field(100.0, env="DEFAULT_SLAB_AREA")  # 默认板面积（平方米）
    
    # AI分析配置
    ENABLE_GPT_ANALYSIS: bool = Field(True, env="ENABLE_GPT_ANALYSIS")  # 是否启用GPT分析
    FALLBACK_TO_TRADITIONAL: bool = Field(True, env="FALLBACK_TO_TRADITIONAL")  # AI失败时是否降级到传统方法
    
    # Redis 配置 (统一使用数据库1)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1

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

    # OpenAI Vision切片配置
    VISION_SLICE_MAX_RESOLUTION: int = Field(2048, env="VISION_SLICE_MAX_RESOLUTION")
    VISION_SLICE_OVERLAP_RATIO: float = Field(0.1, env="VISION_SLICE_OVERLAP_RATIO")
    VISION_SLICE_MIN_SIZE: int = Field(512, env="VISION_SLICE_MIN_SIZE")
    VISION_SLICE_QUALITY: int = Field(95, env="VISION_SLICE_QUALITY")

    class Config:
        case_sensitive = True

class AnalysisSettings:
    """分析配置设置"""
    MAX_SLICES_PER_BATCH = 8
    OCR_CACHE_TTL = 3600  # OCR缓存过期时间（秒）
    VISION_API_TIMEOUT = 60  # Vision API超时时间（秒）
    COORDINATE_TRANSFORM_PRECISION = 2  # 坐标转换精度
    MAX_RETRY_ATTEMPTS = 3  # 最大重试次数
    BATCH_PROCESSING_DELAY = 0.5  # 批次间延迟（秒）
    
    # OCR缓存策略优先级
    OCR_CACHE_PRIORITY = [
        "global_cache",      # 最高优先级
        "shared_slice",      # 中等优先级  
        "single_slice"       # 最低优先级
    ]

settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.MODEL_PATH, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True) 