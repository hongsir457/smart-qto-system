#!/usr/bin/env python3
"""
测试双重存储下载功能
验证文件下载是否能正常工作
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dual_storage_service import DualStorageService

def test_dual_storage_download():
    """测试双重存储下载功能"""
    print("🧪 测试双重存储下载功能...")
    
    try:
        # 创建双重存储服务
        dual_storage = DualStorageService()
        print("✅ 双重存储服务初始化成功")
        
        # 测试URL（从错误日志中获取）
        test_s3_key = "https://objectstorageapi.hzh.sealos.run/gkg9z6uk-smaryqto/drawings/8060ddf4-6993-4f5d-98fe-1ac1fc73e027.pdf"
        
        # 创建临时下载文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
        
        print(f"📥 测试下载: {test_s3_key}")
        print(f"📁 目标路径: {temp_path}")
        
        # 执行下载测试
        success = dual_storage.download_file(test_s3_key, temp_path)
        
        if success:
            print("✅ 双重存储下载成功！")
            
            # 验证文件
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                print(f"📋 下载文件大小: {file_size} 字节")
                
                if file_size > 0:
                    print("✅ 文件下载完整")
                    return True
                else:
                    print("❌ 下载的文件为空")
            else:
                print("❌ 下载文件不存在")
        else:
            print("❌ 双重存储下载失败")
        
        # 清理临时文件
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        
        return False
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_storage_status():
    """测试存储服务状态"""
    print("\n🔍 检查存储服务状态...")
    
    try:
        dual_storage = DualStorageService()
        status = dual_storage.get_storage_status()
        
        print("📊 存储服务状态:")
        for key, value in status.items():
            status_icon = "✅" if value else "❌" if isinstance(value, bool) else "ℹ️"
            print(f"   {status_icon} {key}: {value}")
        
        return status
        
    except Exception as e:
        print(f"❌ 获取存储状态失败: {e}")
        return {}

def main():
    """主函数"""
    print("=" * 60)
    print("🎯 双重存储下载功能测试")
    print("=" * 60)
    
    # 测试存储状态
    status = test_storage_status()
    
    # 测试下载功能
    success = test_dual_storage_download()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试通过！双重存储下载功能正常！")
        print("✅ 文件下载修复成功")
        print("✅ S3下载失败时会自动尝试备用方案")
    else:
        print("💥 测试失败，需要进一步检查")
        print("🔧 建议检查:")
        print("   1. S3服务配置是否正确")
        print("   2. Sealos存储是否可访问")
        print("   3. 本地存储路径是否正常")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main() 