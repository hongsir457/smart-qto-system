import redis
import sys
import os
from celery import Celery
from app.core.config import settings

def test_redis_connection():
    """测试Redis连接"""
    print("🔍 测试Redis连接...")
    try:
        # 从设置获取Redis配置
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        print("✅ Redis连接成功!")
        
        # 测试基本操作
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        redis_client.delete("test_key")
        
        if value and value.decode() == "test_value":
            print("✅ Redis读写操作正常!")
        else:
            print("❌ Redis读写操作失败!")
            
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

def test_celery_broker():
    """测试Celery broker连接"""
    print("\n🔍 测试Celery broker连接...")
    try:
        # 创建测试用的Celery实例
        test_celery = Celery('test_app')
        test_celery.conf.broker_url = settings.CELERY_BROKER_URL
        test_celery.conf.result_backend = settings.CELERY_RESULT_BACKEND
        
        # 测试连接
        with test_celery.connection() as conn:
            conn.connect()
            print("✅ Celery broker连接成功!")
            return True
    except Exception as e:
        print(f"❌ Celery broker连接失败: {e}")
        return False

def test_worker_status():
    """测试Celery worker状态"""
    print("\n🔍 检查Celery worker状态...")
    try:
        from app.core.celery_app import celery_app
        
        # 获取活跃workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print(f"✅ 发现活跃的workers: {list(active_workers.keys())}")
            return True
        else:
            print("❌ 没有发现活跃的workers")
            return False
    except Exception as e:
        print(f"❌ 检查worker状态失败: {e}")
        return False

def suggest_solutions():
    """建议解决方案"""
    print("\n💡 解决方案建议:")
    print("1. 确保Redis服务正在运行:")
    print("   - Windows: 下载并启动Redis服务器")
    print("   - 或者使用Docker: docker run -d -p 6379:6379 redis:alpine")
    print()
    print("2. 启动Celery worker:")
    print("   cd backend")
    print("   celery -A app.core.celery_app worker --loglevel=info --pool=solo")
    print()
    print("3. 如果仍有问题，检查防火墙和端口占用")

def main():
    """主测试函数"""
    print("=" * 50)
    print("🧪 Celery和Redis连接测试")
    print("=" * 50)
    
    # 显示当前配置
    print(f"📝 当前配置:")
    print(f"   Redis URL: {settings.REDIS_URL}")
    print(f"   Celery Broker: {settings.CELERY_BROKER_URL}")
    print(f"   Celery Backend: {settings.CELERY_RESULT_BACKEND}")
    print()
    
    # 运行测试
    redis_ok = test_redis_connection()
    broker_ok = test_celery_broker()
    worker_ok = test_worker_status()
    
    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"   Redis连接: {'✅ 正常' if redis_ok else '❌ 失败'}")
    print(f"   Celery Broker: {'✅ 正常' if broker_ok else '❌ 失败'}")
    print(f"   Celery Worker: {'✅ 正常' if worker_ok else '❌ 失败'}")
    
    if not (redis_ok and broker_ok and worker_ok):
        suggest_solutions()
    else:
        print("\n🎉 所有组件运行正常!")
    
    print("=" * 50)

if __name__ == "__main__":
    main() 