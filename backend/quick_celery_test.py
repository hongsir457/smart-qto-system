#!/usr/bin/env python3
"""
快速Celery测试脚本
用于验证Worker是否正常启动和处理任务
"""
import tempfile
import time

def quick_test():
    """快速测试Celery Worker"""
    print("🚀 快速Celery Worker测试")
    print("=" * 50)
    
    try:
        # 检查Worker是否运行
        from app.core.celery_app import celery_app
        inspect = celery_app.control.inspect()
        
        active_workers = inspect.active()
        
        if not active_workers:
            print("❌ 没有发现活跃的Celery Worker!")
            print("\n💡 请先启动Worker:")
            print("celery -A app.core.celery_app worker --loglevel=info --pool=solo")
            return False
        
        print("✅ 发现活跃的Worker")
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            f.write(b"test content")
            test_file = f.name
        
        print(f"📝 创建测试文件: {test_file}")
        
        # 派发任务
        from app.tasks.ocr_tasks import process_ocr_file_task
        result = process_ocr_file_task.delay(test_file, {})
        
        print(f"📤 任务已派发: {result.id}")
        print("⏳ 等待任务完成...")
        
        # 等待结果（最多15秒）
        try:
            task_result = result.get(timeout=15)
            print("✅ 任务执行成功!")
            print(f"   结果: {task_result}")
            return True
            
        except Exception as e:
            print(f"❌ 任务执行失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = quick_test()
    if success:
        print("\n🎉 Celery Worker工作正常!")
    else:
        print("\n🚨 请检查Celery Worker状态") 