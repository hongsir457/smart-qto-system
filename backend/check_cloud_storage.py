#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
云存储配置检查脚本
检查S3和Sealos存储配置状态
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
from app.services.s3_storage import S3Storage
from app.services.sealos_storage import SealosStorage

async def check_s3_storage():
    """检查S3存储配置"""
    print("🔍 检查S3存储配置...")
    print("-" * 40)
    
    # 检查配置项
    config_items = {
        'S3_ENDPOINT': settings.S3_ENDPOINT,
        'S3_ACCESS_KEY': settings.S3_ACCESS_KEY,
        'S3_SECRET_KEY': settings.S3_SECRET_KEY,
        'S3_BUCKET': settings.S3_BUCKET,
        'S3_REGION': settings.S3_REGION
    }
    
    for key, value in config_items.items():
        status = "✅" if value else "❌"
        display_value = value if key not in ['S3_ACCESS_KEY', 'S3_SECRET_KEY'] else ('***' if value else '')
        print(f"  {status} {key}: {display_value}")
    
    # 检查连接
    try:
        storage = S3Storage()
        if not storage.use_local_fallback:
            print("\n🔧 测试S3连接...")
            
            # 测试上传
            test_data = b"S3 connection test"
            test_path = "test/connection_check.txt"
            
            url = await storage.upload_file(test_data, test_path, "text/plain")
            print(f"  ✅ 上传测试成功: {url}")
            
            # 测试下载
            downloaded = await storage.download_file(url)
            if downloaded == test_data:
                print("  ✅ 下载测试成功")
            else:
                print("  ❌ 下载测试失败")
                return False
            
            # 清理测试文件
            await storage.delete_file(test_path)
            print("  ✅ 清理测试文件成功")
            
            print("🎉 S3存储配置正常")
            return True
        else:
            print("⚠️  S3配置不完整，将使用本地存储")
            return False
            
    except Exception as e:
        print(f"❌ S3存储测试失败: {e}")
        return False

async def check_sealos_storage():
    """检查Sealos存储配置"""
    print("\n🔍 检查Sealos存储配置...")
    print("-" * 40)
    
    # 检查配置项
    config_items = {
        'SEALOS_STORAGE_URL': settings.SEALOS_STORAGE_URL,
        'SEALOS_ACCESS_KEY': settings.SEALOS_ACCESS_KEY,
        'SEALOS_SECRET_KEY': settings.SEALOS_SECRET_KEY,
        'SEALOS_BUCKET_NAME': settings.SEALOS_BUCKET_NAME
    }
    
    for key, value in config_items.items():
        status = "✅" if value else "❌"
        display_value = value if key not in ['SEALOS_ACCESS_KEY', 'SEALOS_SECRET_KEY'] else ('***' if value else '')
        print(f"  {status} {key}: {display_value}")
    
    # 检查连接
    try:
        storage = SealosStorage()
        if not storage.use_local_fallback:
            print("\n🔧 测试Sealos连接...")
            
            # 测试上传
            test_data = b"Sealos connection test"
            test_path = "test/sealos_connection_check.txt"
            
            url = await storage.upload_file(test_data, test_path, "text/plain")
            print(f"  ✅ 上传测试成功: {url}")
            
            # 测试下载
            downloaded = await storage.download_file(url)
            if downloaded == test_data:
                print("  ✅ 下载测试成功")
            else:
                print("  ❌ 下载测试失败")
                return False
            
            # 清理测试文件
            await storage.delete_file(test_path)
            print("  ✅ 清理测试文件成功")
            
            print("🎉 Sealos存储配置正常")
            return True
        else:
            print("⚠️  Sealos配置不完整，将使用本地存储")
            return False
            
    except Exception as e:
        print(f"❌ Sealos存储测试失败: {e}")
        return False

def check_local_storage():
    """检查本地存储目录"""
    print("\n🔍 检查本地存储目录...")
    print("-" * 40)
    
    directories = [
        Path("storage/s3_fallback"),
        Path("storage/sealos_fallback"),
        Path("uploads"),
        Path("exports")
    ]
    
    for directory in directories:
        if directory.exists():
            print(f"  ✅ {directory}: 存在")
        else:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ {directory}: 已创建")
            except Exception as e:
                print(f"  ❌ {directory}: 创建失败 - {e}")

def print_recommendations(s3_ok: bool, sealos_ok: bool):
    """打印配置建议"""
    print("\n" + "=" * 60)
    print("📋 配置建议")
    print("=" * 60)
    
    if s3_ok and sealos_ok:
        print("🎉 所有云存储配置正常！")
        print("   系统将优先使用S3存储，Sealos存储作为备用")
    elif s3_ok:
        print("✅ S3存储配置正常")
        print("⚠️  Sealos存储配置不完整，建议配置作为备用")
        print("   运行: python setup_cloud_storage.py")
    elif sealos_ok:
        print("✅ Sealos存储配置正常")
        print("⚠️  S3存储配置不完整，建议配置获得更好兼容性")
        print("   运行: python setup_cloud_storage.py")
    else:
        print("❌ 所有云存储都未配置")
        print("   系统将使用本地存储，功能受限")
        print("   建议运行配置向导: python setup_cloud_storage.py")
    
    print("\n📚 配置参考:")
    print("   - .env 文件: 存储配置参数")
    print("   - env.example: 配置示例文件")
    print("   - 配置向导: python setup_cloud_storage.py")
    print("   - 依赖安装: PowerShell install_cloud_storage_deps.ps1")

async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 智能工程量计算系统 - 云存储配置检查")
    print("=" * 60)
    
    # 检查本地存储
    check_local_storage()
    
    # 检查云存储
    s3_ok = await check_s3_storage()
    sealos_ok = await check_sealos_storage()
    
    # 打印建议
    print_recommendations(s3_ok, sealos_ok)
    
    print("\n✨ 检查完成")

if __name__ == "__main__":
    asyncio.run(main()) 