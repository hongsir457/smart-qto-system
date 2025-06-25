#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新架构系统启动脚本
完整启动流程：数据库初始化 → 测试用户创建 → Redis检查 → Celery启动 → FastAPI启动
"""

import os
import sys
import subprocess
import time
import logging
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_redis_connection():
    """检查Redis连接"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=1)
        r.ping()
        logger.info("✅ Redis连接正常")
        return True
    except Exception as e:
        logger.error(f"❌ Redis连接失败: {str(e)}")
        logger.info("请确保Redis服务已启动")
        return False

def init_database():
    """初始化数据库"""
    try:
        logger.info("📂 初始化数据库...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ 数据库初始化完成")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {str(e)}")
        return False

def create_test_user():
    """创建测试用户"""
    try:
        logger.info("👤 创建测试用户...")
        
        db = SessionLocal()
        
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == "testuser").first()
        
        if existing_user:
            logger.info("✅ 测试用户已存在")
            db.close()
            return True
        
        # 创建新用户
        test_user = User(
            username="testuser",
            email="test@example.com",
            full_name="测试用户",
            hashed_password=get_password_hash("testpass123"),
            is_active=True
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        db.close()
        
        logger.info(f"✅ 测试用户创建成功: ID={test_user.id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 创建测试用户失败: {str(e)}")
        return False

def check_dependencies():
    """检查关键依赖"""
    logger.info("🔍 检查依赖...")
    
    dependencies = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("celery", "Celery"),
        ("redis", "Redis客户端"),
        ("sqlalchemy", "SQLAlchemy"),
        ("boto3", "AWS SDK"),
        ("openpyxl", "Excel处理"),
    ]
    
    missing = []
    for module, name in dependencies:
        try:
            __import__(module)
            logger.info(f"✅ {name}")
        except ImportError:
            logger.error(f"❌ {name} - 未安装")
            missing.append(name)
    
    if missing:
        logger.error(f"请安装缺失的依赖: {', '.join(missing)}")
        return False
    
    return True

def start_celery_worker():
    """启动Celery Worker（异步）"""
    try:
        logger.info("🔧 启动Celery Worker...")
        
        # Windows下启动Celery
        cmd = [
            "celery", "-A", "app.core.celery_app", "worker",
            "--loglevel=info",
            "--pool=solo",  # Windows推荐使用solo池
            "--concurrency=1"
        ]
        
        # 异步启动Celery进程
        process = subprocess.Popen(
            cmd,
            cwd=Path(__file__).parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # 等待一下确保启动
        time.sleep(3)
        
        if process.poll() is None:
            logger.info("✅ Celery Worker已启动")
            return process
        else:
            logger.error("❌ Celery Worker启动失败")
            return None
            
    except Exception as e:
        logger.error(f"❌ 启动Celery Worker异常: {str(e)}")
        return None

def start_fastapi():
    """启动FastAPI服务器"""
    try:
        logger.info("🚀 启动FastAPI服务器...")
        
        cmd = [
            "uvicorn", "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ]
        
        # 启动FastAPI
        process = subprocess.Popen(
            cmd,
            cwd=Path(__file__).parent
        )
        
        logger.info("✅ FastAPI服务器已启动在 http://localhost:8000")
        return process
        
    except Exception as e:
        logger.error(f"❌ 启动FastAPI失败: {str(e)}")
        return None

def main():
    """主启动流程"""
    print("🚀 智能工程量计算系统 - 新架构启动")
    print("=" * 80)
    
    # 1. 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，请安装缺失的包")
        return 1
    
    # 2. 检查Redis
    if not check_redis_connection():
        print("❌ Redis连接失败，请启动Redis服务")
        return 1
    
    # 3. 初始化数据库
    if not init_database():
        print("❌ 数据库初始化失败")
        return 1
    
    # 4. 创建测试用户
    if not create_test_user():
        print("❌ 创建测试用户失败")
        return 1
    
    # 5. 启动Celery Worker
    celery_process = start_celery_worker()
    if not celery_process:
        print("❌ Celery Worker启动失败")
        return 1
    
    # 6. 启动FastAPI
    fastapi_process = start_fastapi()
    if not fastapi_process:
        print("❌ FastAPI启动失败")
        if celery_process:
            celery_process.terminate()
        return 1
    
    print("=" * 80)
    print("🎉 系统启动完成！")
    print("📊 FastAPI文档: http://localhost:8000/docs")
    print("🔍 Redis连接: localhost:6379")
    print("👤 测试用户: testuser / testpass123")
    print("=" * 80)
    print("💡 现在可以运行测试: python test_new_architecture.py")
    print("⛔ 按 Ctrl+C 停止系统")
    
    try:
        # 等待进程
        fastapi_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止系统...")
        
        if fastapi_process:
            fastapi_process.terminate()
            logger.info("✅ FastAPI已停止")
        
        if celery_process:
            celery_process.terminate()
            logger.info("✅ Celery Worker已停止")
        
        print("👋 系统已停止")
    
    return 0

if __name__ == "__main__":
    exit(main())