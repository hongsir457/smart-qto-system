#!/usr/bin/env python3
"""
智能工程量计算系统状态检查脚本
"""

import sys
import os
import redis
import requests
import asyncio
import json
from pathlib import Path

# 添加backend路径
backend_path = Path(__file__).parent / "backend"
sys.path.append(str(backend_path))

def check_redis_connection():
    """检查Redis连接"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        r.ping()
        info = r.info()
        print(f"✅ Redis服务正常 - 版本: {info.get('redis_version', 'Unknown')}")
        print(f"   - 连接数: {info.get('connected_clients', 0)}")
        print(f"   - 内存使用: {info.get('used_memory_human', 'Unknown')}")
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

def check_fastapi_server():
    """检查FastAPI服务器"""
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI服务器正常运行")
            return True
        else:
            print(f"⚠️ FastAPI服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ FastAPI服务器未启动或无法连接")
        return False
    except Exception as e:
        print(f"❌ FastAPI服务器检查失败: {e}")
        return False

def check_storage_services():
    """检查存储服务配置"""
    try:
        from app.services.dual_storage_service import DualStorageService
        ds = DualStorageService()
        
        print(f"✅ 存储服务配置正常")
        print(f"   - 主存储: {ds.primary_storage.__class__.__name__}")
        print(f"   - S3存储桶: {ds.s3_service.bucket_name}")
        print(f"   - S3端点: {ds.s3_service.endpoint_url}")
        
        # 检查S3配置完整性
        s3_config_complete = all([
            ds.s3_service.endpoint_url,
            ds.s3_service.access_key,
            ds.s3_service.secret_key,
            ds.s3_service.bucket_name
        ])
        
        if s3_config_complete:
            print("   - S3配置: ✅ 完整")
        else:
            print("   - S3配置: ⚠️ 不完整")
        
        return True
    except Exception as e:
        print(f"❌ 存储服务检查失败: {e}")
        return False

def check_celery_worker():
    """检查Celery Worker状态"""
    try:
        from app.core.celery_app import celery_app
        
        # 检查活跃的worker
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print("✅ Celery Worker正常运行")
            for worker_name, tasks in active_workers.items():
                print(f"   - Worker: {worker_name}")
                print(f"   - 活跃任务数: {len(tasks)}")
        else:
            print("⚠️ 没有检测到活跃的Celery Worker")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Celery Worker检查失败: {e}")
        return False

def check_database_connection():
    """检查数据库连接"""
    try:
        from app.core.database import get_db
        from app.models.drawing import Drawing
        
        # 尝试查询数据库
        db = next(get_db())
        count = db.query(Drawing).count()
        print(f"✅ 数据库连接正常 - 图纸记录数: {count}")
        db.close()
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_ai_services():
    """检查AI服务配置"""
    try:
        from app.core.config import settings
        
        openai_configured = bool(settings.OPENAI_API_KEY)
        print(f"OpenAI API: {'✅ 已配置' if openai_configured else '⚠️ 未配置'}")
        
        if openai_configured:
            print(f"   - 模型: {settings.OPENAI_MODEL}")
            print(f"   - 最大tokens: {settings.OPENAI_MAX_TOKENS}")
        
        return openai_configured
    except Exception as e:
        print(f"❌ AI服务检查失败: {e}")
        return False

def main():
    """主检查函数"""
    print("🔍 智能工程量计算系统状态检查")
    print("=" * 50)
    
    checks = [
        ("Redis服务", check_redis_connection),
        ("FastAPI服务器", check_fastapi_server),
        ("存储服务", check_storage_services),
        ("数据库连接", check_database_connection),
        ("Celery Worker", check_celery_worker),
        ("AI服务配置", check_ai_services),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n📋 检查 {check_name}:")
        try:
            if check_func():
                passed += 1
        except Exception as e:
            print(f"❌ 检查过程中发生异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 系统状态总结: {passed}/{total} 项检查通过")
    
    if passed == total:
        print("🎉 系统运行状态良好！所有组件正常工作。")
        print("\n💡 您现在可以：")
        print("   - 上传建筑图纸进行分析")
        print("   - 查看实时任务进度")
        print("   - 导出工程量清单")
    elif passed >= total * 0.8:
        print("⚠️ 系统基本正常，但有部分组件需要注意。")
    else:
        print("❌ 系统存在较多问题，建议检查配置和服务状态。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 