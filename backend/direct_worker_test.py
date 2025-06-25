#!/usr/bin/env python3
"""
直接Worker测试脚本
直接连接到Worker正在使用的Redis数据库进行测试
"""
import redis
from celery import Celery

def test_direct_connection():
    """直接测试连接"""
    print("🔗 直接Worker连接测试")
    print("=" * 50)
    
    try:
        # 1. 直接连接Redis数据库1（Worker使用的数据库）
        print("1️⃣ 连接Redis数据库1...")
        redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        redis_client.ping()
        print("✅ Redis连接成功")
        
        # 2. 创建Celery实例，使用相同配置
        print("2️⃣ 创建Celery实例...")
        celery_app = Celery('test')
        celery_app.conf.update(
            broker_url='redis://localhost:6379/1',
            result_backend='redis://localhost:6379/1'
        )
        print("✅ Celery实例创建成功")
        
        # 3. 检查活跃Worker
        print("3️⃣ 检查活跃Worker...")
        inspect = celery_app.control.inspect()
        active = inspect.active()
        
        if active:
            print(f"✅ 发现 {len(active)} 个活跃Worker:")
            for worker_name, tasks in active.items():
                print(f"   • Worker: {worker_name}")
                print(f"     任务数: {len(tasks)}")
            return True
        else:
            print("❌ 没有发现活跃Worker")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_task():
    """测试简单任务派发"""
    print("\n🚀 测试任务派发")
    print("=" * 50)
    
    try:
        # 导入OCR任务
        from app.tasks.ocr_tasks import process_ocr_file_task
        
        # 创建测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            f.write(b"test content")
            test_file = f.name
        
        print(f"📝 测试文件: {test_file}")
        
        # 派发任务
        print("📤 派发任务...")
        result = process_ocr_file_task.delay(test_file, {"test": True})
        print(f"✅ 任务已派发: {result.id}")
        
        # 等待结果
        print("⏳ 等待结果 (超时10秒)...")
        task_result = result.get(timeout=10)
        print("✅ 任务完成!")
        print(f"📋 结果: {task_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 任务测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🎯 直接Worker测试工具")
    print("=" * 50)
    
    # 测试连接
    connection_ok = test_direct_connection()
    
    if connection_ok:
        print("\n" + "=" * 50)
        # 测试任务派发
        task_ok = test_simple_task()
        
        if task_ok:
            print("\n🎉 所有测试通过！Worker工作正常！")
        else:
            print("\n⚠️ 连接正常但任务执行失败")
    else:
        print("\n🚨 Worker连接失败，请检查Worker是否启动") 