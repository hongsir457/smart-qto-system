import redis
from app.core.config import settings

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    
    def get(self, key: str):
        """获取缓存"""
        return self.redis_client.get(key)
    
    def set(self, key: str, value: str, timeout: int = None):
        """设置缓存"""
        self.redis_client.set(key, value, ex=timeout)
    
    def delete(self, key: str):
        """删除缓存"""
        self.redis_client.delete(key)
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self.redis_client.exists(key)

cache_manager = CacheManager() 