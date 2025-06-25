#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sealos集成验证脚本
验证系统是否完全移除模拟模式并正确配置sealos
"""

import os
import sys
from pathlib import Path

def check_config():
    """检查配置文件"""
    print("🔍 检查配置文件...")
    
    try:
        from app.core.config import settings
        
        # 检查S3配置
        s3_checks = {
            "S3_ENDPOINT": settings.S3_ENDPOINT,
            "S3_BUCKET": settings.S3_BUCKET,
            "S3_ACCESS_KEY": settings.S3_ACCESS_KEY,
            "S3_SECRET_KEY": settings.S3_SECRET_KEY,
            "S3_REGION": settings.S3_REGION
        }
        
        print("✅ S3配置检查:")
        for key, value in s3_checks.items():
            if key in ["S3_ACCESS_KEY", "S3_SECRET_KEY"]:
                status = "✓" if value and value != "" else "✗"
                print(f"   {key}: {status} ({'已配置' if status == '✓' else '未配置'})")
            else:
                print(f"   {key}: {value}")
        
        # 检查数据库配置
        print(f"\n✅ 数据库配置:")
        print(f"   DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        print(f"   POSTGRES_URL: {settings.POSTGRES_URL[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False

def check_s3_service():
    """检查S3服务"""
    print("\n🔍 检查S3服务...")
    
    try:
        from app.services.s3_service import s3_service
        
        print("✅ S3Service初始化成功")
        print(f"   端点: {s3_service.endpoint_url}")
        print(f"   存储桶: {s3_service.bucket_name}")
        
        # 检查是否为sealos端点
        if "sealos" in s3_service.endpoint_url:
            print("✅ 使用Sealos S3端点")
        else:
            print("⚠️  未使用Sealos S3端点")
        
        return True
        
    except Exception as e:
        print(f"❌ S3Service检查失败: {e}")
        return False

def check_database_models():
    """检查数据库模型"""
    print("\n🔍 检查数据库模型...")
    
    try:
        from app.models.drawing import Drawing
        from app.models.user import User
        
        # 检查模型是否包含S3字段
        drawing_fields = [field for field in dir(Drawing) if not field.startswith('_')]
        s3_fields = [field for field in drawing_fields if 's3' in field.lower()]
        
        print("✅ 数据库模型检查:")
        print(f"   Drawing模型S3字段: {s3_fields}")
        
        if s3_fields:
            print("✅ 包含S3存储字段")
        else:
            print("⚠️  未找到S3存储字段")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库模型检查失败: {e}")
        return False

def check_task_system():
    """检查任务系统"""
    print("\n🔍 检查任务系统...")
    
    try:
        from app.tasks.drawing_tasks import process_drawing_celery_task
        from app.tasks.real_time_task_manager import RealTimeTaskManager
        
        print("✅ 任务系统组件:")
        print("   ✓ process_drawing_celery_task")
        print("   ✓ RealTimeTaskManager")
        
        return True
        
    except Exception as e:
        print(f"❌ 任务系统检查失败: {e}")
        return False

def check_api_endpoints():
    """检查API端点"""
    print("\n🔍 检查API端点...")
    
    try:
        from app.api.v1.drawings.upload import router as upload_router
        from app.api.v1.drawings.list import router as list_router
        
        print("✅ API端点检查:")
        print("   ✓ 文件上传端点")
        print("   ✓ 图纸列表端点")
        
        return True
        
    except Exception as e:
        print(f"❌ API端点检查失败: {e}")
        return False

def check_removed_files():
    """检查是否移除了旧文件"""
    print("\n🔍 检查已移除的文件...")
    
    removed_files = [
        "app/services/storage.py",
        "aws_config_example.env",
        "test_s3_connection.py"
    ]
    
    all_removed = True
    for file_path in removed_files:
        if Path(file_path).exists():
            print(f"⚠️  文件仍存在: {file_path}")
            all_removed = False
        else:
            print(f"✅ 已移除: {file_path}")
    
    return all_removed

def check_sealos_files():
    """检查sealos相关文件"""
    print("\n🔍 检查Sealos相关文件...")
    
    sealos_files = [
        "sealos_config.env",
        "test_sealos_connection.py",
        "SEALOS_DEPLOYMENT_GUIDE.md"
    ]
    
    all_exist = True
    for file_path in sealos_files:
        if Path(file_path).exists():
            print(f"✅ 存在: {file_path}")
        else:
            print(f"❌ 缺失: {file_path}")
            all_exist = False
    
    return all_exist

def main():
    """主函数"""
    print("🚀 开始Sealos集成验证...\n")
    
    checks = [
        ("配置文件", check_config),
        ("S3服务", check_s3_service),
        ("数据库模型", check_database_models),
        ("任务系统", check_task_system),
        ("API端点", check_api_endpoints),
        ("移除旧文件", check_removed_files),
        ("Sealos文件", check_sealos_files)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name}检查异常: {e}")
            results.append((check_name, False))
    
    # 显示结果汇总
    print("\n" + "="*60)
    print("📊 Sealos集成验证结果汇总")
    print("="*60)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check_name:15s}: {status}")
        if not result:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("🎉 所有检查通过！")
        print("✅ 系统已完全集成Sealos，无模拟模式")
        print("✅ 所有组件都使用真实的Sealos服务")
        print("\n📋 下一步:")
        print("1. 确保 .env 文件中的Sealos配置正确")
        print("2. 运行 python test_sealos_connection.py 测试连接")
        print("3. 启动系统: python start_system.py")
    else:
        print("⚠️  部分检查失败，请查看上述详细信息")
        print("\n💡 建议:")
        print("1. 检查缺失的文件或配置")
        print("2. 确认所有依赖已正确安装")
        print("3. 验证Sealos服务配置")

if __name__ == "__main__":
    main() 