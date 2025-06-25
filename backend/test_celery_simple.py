#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的 Celery 任务测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.celery_app import celery_app
from app.tasks.drawing_tasks import process_drawing_celery_task

def test_celery_connection():
    """测试 Celery 连接"""
    
    print("🔍 测试 Celery 连接...")
    
    try:
        # 检查 Celery 应用
        print(f"Celery 应用名称: {celery_app.main}")
        print(f"Broker URL: {celery_app.conf.broker_url}")
        print(f"Result Backend: {celery_app.conf.result_backend}")
        
        # 检查注册的任务
        print("\n📋 注册的任务:")
        for task_name in celery_app.tasks:
            if 'drawing' in task_name.lower():
                print(f"  - {task_name}")
        
        # 检查 Worker 状态
        print("\n🔍 检查 Worker 状态...")
        inspect = celery_app.control.inspect()
        
        # 获取活跃的 Worker
        active_workers = inspect.active()
        if active_workers:
            print(f"✅ 活跃的 Worker: {list(active_workers.keys())}")
            
            # 检查每个 Worker 的注册任务
            registered = inspect.registered()
            for worker, tasks in registered.items():
                print(f"\nWorker {worker} 注册的任务:")
                for task in tasks:
                    if 'drawing' in task:
                        print(f"  ✓ {task}")
        else:
            print("⚠️ 没有活跃的 Worker")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Celery 连接测试失败: {str(e)}")
        return False

def test_task_submission():
    """测试任务提交"""
    
    print("\n🚀 测试任务提交...")
    
    try:
        # 创建测试参数
        test_params = {
            'file_path': '/tmp/test.pdf',
            'drawing_id': 'test_123',
            'user_id': '1',
            'db_drawing_id': 999,
            'task_id': 'test_task_123'
        }
        
        # 提交任务（不执行，只测试提交）
        print("提交测试任务...")
        result = process_drawing_celery_task.delay(**test_params)
        
        print(f"✅ 任务提交成功，Celery 任务ID: {result.id}")
        print(f"任务状态: {result.status}")
        
        # 等待一小段时间看任务状态
        import time
        time.sleep(2)
        
        print(f"2秒后任务状态: {result.status}")
        
        # 取消任务（因为这只是测试）
        result.revoke(terminate=True)
        print("✅ 测试任务已取消")
        
        return True
        
    except Exception as e:
        print(f"❌ 任务提交测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 开始 Celery 简单测试")
    print("=" * 50)
    
    # 测试连接
    connection_ok = test_celery_connection()
    
    if connection_ok:
        # 测试任务提交
        submission_ok = test_task_submission()
        
        if submission_ok:
            print("\n🎉 所有测试通过！Celery 配置正确")
        else:
            print("\n❌ 任务提交测试失败")
    else:
        print("\n❌ Celery 连接测试失败")
        print("\n💡 请确保:")
        print("1. Redis 服务正在运行")
        print("2. Celery Worker 已启动: celery -A app.core.celery_app worker --loglevel=info")