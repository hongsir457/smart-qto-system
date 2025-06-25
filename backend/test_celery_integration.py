#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Celery 集成是否正常工作
"""

import asyncio
import logging
import requests
import json
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_celery_integration():
    """测试 Celery 集成"""
    
    base_url = "http://localhost:8000"
    
    # 1. 获取访问令牌
    logger.info("1. 获取访问令牌...")
    login_response = requests.post(
        f"{base_url}/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    
    if login_response.status_code != 200:
        logger.error(f"登录失败: {login_response.status_code} - {login_response.text}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info("✅ 成功获取访问令牌")
    
    # 2. 创建测试文件
    logger.info("2. 创建测试文件...")
    test_content = b"Test PDF content for Celery integration"
    
    files = {
        'file': ('test_celery.pdf', test_content, 'application/pdf')
    }
    
    # 3. 上传文件（使用新的 Celery 任务）
    logger.info("3. 上传文件到 Celery 任务...")
    upload_response = requests.post(
        f"{base_url}/api/v1/drawings/upload",
        files=files,
        headers=headers
    )
    
    if upload_response.status_code != 200:
        logger.error(f"上传失败: {upload_response.status_code} - {upload_response.text}")
        return False
    
    upload_data = upload_response.json()
    task_id = upload_data.get("task_id")
    drawing_id = upload_data.get("id")
    
    logger.info(f"✅ 文件上传成功，任务ID: {task_id}, 图纸ID: {drawing_id}")
    
    # 4. 监控任务进度
    logger.info("4. 监控 Celery 任务进度...")
    
    for i in range(30):  # 最多等待30秒
        time.sleep(1)
        
        # 获取图纸状态
        status_response = requests.get(
            f"{base_url}/api/v1/drawings/{drawing_id}",
            headers=headers
        )
        
        if status_response.status_code == 200:
            drawing_data = status_response.json()
            status = drawing_data.get("status")
            
            logger.info(f"第 {i+1} 秒 - 图纸状态: {status}")
            
            if status in ["completed", "failed"]:
                logger.info(f"✅ Celery 任务完成，最终状态: {status}")
                
                if status == "completed":
                    logger.info("🎉 Celery 集成测试成功！")
                    return True
                else:
                    logger.error(f"❌ Celery 任务失败，错误: {drawing_data.get('error_message')}")
                    return False
    
    logger.error("⏰ Celery 任务超时，测试失败")
    return False

def test_celery_worker_status():
    """检查 Celery Worker 状态"""
    
    logger.info("检查 Celery Worker 状态...")
    
    try:
        from app.core.celery_app import celery_app
        
        # 检查活跃的 Worker
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            logger.info(f"✅ 发现活跃的 Celery Worker: {list(active_workers.keys())}")
            
            # 检查注册的任务
            registered = inspect.registered()
            for worker, tasks in registered.items():
                logger.info(f"Worker {worker} 注册的任务:")
                for task in tasks:
                    if 'drawing' in task:
                        logger.info(f"  - {task}")
            
            return True
        else:
            logger.warning("⚠️ 没有发现活跃的 Celery Worker")
            return False
            
    except Exception as e:
        logger.error(f"❌ 检查 Celery Worker 失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 开始 Celery 集成测试")
    print("=" * 50)
    
    # 检查 Worker 状态
    worker_ok = test_celery_worker_status()
    
    if worker_ok:
        # 运行集成测试
        success = test_celery_integration()
        
        if success:
            print("\n🎉 所有测试通过！Celery 集成正常工作")
        else:
            print("\n❌ 测试失败，请检查日志")
    else:
        print("\n⚠️ Celery Worker 未运行，请先启动 Worker")
        print("运行命令: celery -A app.core.celery_app worker --loglevel=info")