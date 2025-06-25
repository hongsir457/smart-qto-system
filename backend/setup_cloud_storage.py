#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sealos云存储配置设置脚本
帮助用户快速配置云存储服务
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.services.s3_storage import S3Storage
from app.services.sealos_storage import SealosStorage

class CloudStorageSetup:
    """云存储配置类"""
    
    def __init__(self):
        self.config_file = Path(".env")
        self.example_file = Path("env.example")
    
    def print_header(self):
        """打印配置向导头部"""
        print("=" * 60)
        print("🚀 智能工程量计算系统 - 云存储配置向导")
        print("=" * 60)
        print()
        print("本向导将帮助您配置Sealos云存储服务")
        print("支持两种存储方案：")
        print("  1. Sealos S3对象存储（推荐）")
        print("  2. Sealos原生存储API")
        print()
    
    def collect_s3_config(self) -> Dict[str, str]:
        """收集S3存储配置"""
        print("📦 S3对象存储配置")
        print("-" * 30)
        
        config = {}
        
        # S3端点
        default_endpoint = "https://objectstorageapi.hzh.sealos.run"
        endpoint = input(f"S3端点地址 [{default_endpoint}]: ").strip()
        config['S3_ENDPOINT'] = endpoint or default_endpoint
        
        # Access Key
        access_key = input("Access Key: ").strip()
        if not access_key:
            print("❌ Access Key不能为空")
            return {}
        config['S3_ACCESS_KEY'] = access_key
        
        # Secret Key
        secret_key = input("Secret Key: ").strip()
        if not secret_key:
            print("❌ Secret Key不能为空")
            return {}
        config['S3_SECRET_KEY'] = secret_key
        
        # Bucket名称
        default_bucket = "smart-qto-bucket"
        bucket = input(f"Bucket名称 [{default_bucket}]: ").strip()
        config['S3_BUCKET'] = bucket or default_bucket
        
        # 区域
        default_region = "us-east-1"
        region = input(f"区域 [{default_region}]: ").strip()
        config['S3_REGION'] = region or default_region
        
        return config
    
    def collect_sealos_config(self) -> Dict[str, str]:
        """收集Sealos原生存储配置"""
        print("🌊 Sealos原生存储配置")
        print("-" * 30)
        
        config = {}
        
        # 存储URL
        default_url = "https://objectstorageapi.hzh.sealos.run"
        url = input(f"Sealos存储URL [{default_url}]: ").strip()
        config['SEALOS_STORAGE_URL'] = url or default_url
        
        # Access Key（可以与S3共用）
        access_key = input("Sealos Access Key: ").strip()
        if not access_key:
            print("❌ Access Key不能为空")
            return {}
        config['SEALOS_ACCESS_KEY'] = access_key
        
        # Secret Key（可以与S3共用）
        secret_key = input("Sealos Secret Key: ").strip()
        if not secret_key:
            print("❌ Secret Key不能为空")
            return {}
        config['SEALOS_SECRET_KEY'] = secret_key
        
        # Bucket名称
        default_bucket = "smart-qto-system"
        bucket = input(f"Bucket名称 [{default_bucket}]: ").strip()
        config['SEALOS_BUCKET_NAME'] = bucket or default_bucket
        
        return config
    
    def create_env_file(self, s3_config: Dict[str, str], sealos_config: Dict[str, str]):
        """创建.env配置文件"""
        print("\n📝 创建配置文件...")
        
        # 读取示例配置
        env_content = ""
        if self.example_file.exists():
            with open(self.example_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
        else:
            # 基础配置模板
            env_content = """# 智能工程量计算系统配置文件
# 请根据实际情况修改配置值

# === 基础配置 ===
PROJECT_NAME=智能工程量清单系统
DEBUG=false
SECRET_KEY=your-super-secret-key-change-this-in-production

# === 数据库配置 ===
DATABASE_URL=sqlite:///./app/database.db

# === Redis配置 ===
REDIS_URL=redis://localhost:6379/1

# === AI配置 ===
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-2024-11-20
"""
        
        # 更新S3配置
        for key, value in s3_config.items():
            pattern = f"{key}="
            if pattern in env_content:
                # 替换现有配置
                lines = env_content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith(pattern):
                        lines[i] = f"{key}={value}"
                        break
                env_content = '\n'.join(lines)
            else:
                # 添加新配置
                env_content += f"\n{key}={value}"
        
        # 更新Sealos配置
        for key, value in sealos_config.items():
            pattern = f"{key}="
            if pattern in env_content:
                # 替换现有配置
                lines = env_content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith(pattern):
                        lines[i] = f"{key}={value}"
                        break
                env_content = '\n'.join(lines)
            else:
                # 添加新配置
                env_content += f"\n{key}={value}"
        
        # 写入配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ 配置文件已创建: {self.config_file}")
    
    async def test_s3_connection(self, config: Dict[str, str]) -> bool:
        """测试S3连接"""
        print("\n🔧 测试S3存储连接...")
        
        try:
            # 临时设置环境变量
            for key, value in config.items():
                os.environ[key] = value
            
            # 创建S3存储实例
            storage = S3Storage()
            
            # 测试上传小文件
            test_data = b"Hello, Sealos Cloud Storage!"
            test_path = "test/connection_test.txt"
            
            url = await storage.upload_file(test_data, test_path, "text/plain")
            print(f"✅ 文件上传成功: {url}")
            
            # 测试下载
            downloaded_data = await storage.download_file(url)
            if downloaded_data == test_data:
                print("✅ 文件下载验证成功")
            else:
                print("❌ 文件下载验证失败")
                return False
            
            # 测试删除
            if await storage.delete_file(test_path):
                print("✅ 文件删除成功")
            else:
                print("❌ 文件删除失败")
            
            print("🎉 S3存储连接测试通过！")
            return True
            
        except Exception as e:
            print(f"❌ S3存储连接测试失败: {e}")
            return False
    
    async def test_sealos_connection(self, config: Dict[str, str]) -> bool:
        """测试Sealos存储连接"""
        print("\n🔧 测试Sealos存储连接...")
        
        try:
            # 临时设置环境变量
            for key, value in config.items():
                os.environ[key] = value
            
            # 创建Sealos存储实例
            storage = SealosStorage()
            
            # 测试上传小文件
            test_data = b"Hello, Sealos Native Storage!"
            test_path = "test/sealos_connection_test.txt"
            
            url = await storage.upload_file(test_data, test_path, "text/plain")
            print(f"✅ 文件上传成功: {url}")
            
            # 测试下载
            downloaded_data = await storage.download_file(url)
            if downloaded_data == test_data:
                print("✅ 文件下载验证成功")
            else:
                print("❌ 文件下载验证失败")
                return False
            
            # 测试删除
            if await storage.delete_file(test_path):
                print("✅ 文件删除成功")
            else:
                print("❌ 文件删除失败")
            
            print("🎉 Sealos存储连接测试通过！")
            return True
            
        except Exception as e:
            print(f"❌ Sealos存储连接测试失败: {e}")
            return False
    
    def print_usage_guide(self):
        """打印使用指南"""
        print("\n" + "=" * 60)
        print("📚 云存储使用指南")
        print("=" * 60)
        print()
        print("1. 在代码中使用S3存储:")
        print("   ```python")
        print("   from app.services.s3_storage import s3_storage")
        print("   ")
        print("   # 上传文件")
        print("   url = await s3_storage.upload_file(file_data, 'path/file.jpg')")
        print("   ")
        print("   # 下载文件")
        print("   data = await s3_storage.download_file(url)")
        print("   ```")
        print()
        print("2. 在代码中使用Sealos存储:")
        print("   ```python")
        print("   from app.services.sealos_storage import SealosStorage")
        print("   ")
        print("   storage = SealosStorage()")
        print("   url = await storage.upload_file(file_data, 'path/file.jpg')")
        print("   ```")
        print()
        print("3. 存储位置:")
        print("   - 云存储成功: 文件保存在Sealos云端")
        print("   - 云存储失败: 自动降级到本地存储")
        print("   - 本地备份路径: storage/s3_fallback/ 或 storage/sealos_fallback/")
        print()
        print("4. 配置文件位置: .env")
        print("   修改配置后需要重启服务")
        print()
    
    async def run_setup(self):
        """运行配置向导"""
        self.print_header()
        
        # 选择存储方案
        print("请选择存储方案:")
        print("1. S3对象存储（推荐，兼容性好）")
        print("2. Sealos原生存储（功能更丰富）")
        print("3. 同时配置两种方案")
        
        choice = input("\n请输入选择 [1]: ").strip() or "1"
        
        s3_config = {}
        sealos_config = {}
        
        if choice in ["1", "3"]:
            print("\n" + "=" * 40)
            s3_config = self.collect_s3_config()
            if not s3_config:
                print("❌ S3配置失败，退出设置")
                return
        
        if choice in ["2", "3"]:
            print("\n" + "=" * 40)
            sealos_config = self.collect_sealos_config()
            if not sealos_config:
                print("❌ Sealos配置失败，退出设置")
                return
        
        # 创建配置文件
        self.create_env_file(s3_config, sealos_config)
        
        # 测试连接
        if s3_config:
            await self.test_s3_connection(s3_config)
        
        if sealos_config:
            await self.test_sealos_connection(sealos_config)
        
        # 显示使用指南
        self.print_usage_guide()
        
        print("🎉 云存储配置完成！")
        print("请重启服务以应用新配置。")

async def main():
    """主函数"""
    setup = CloudStorageSetup()
    await setup.run_setup()

if __name__ == "__main__":
    asyncio.run(main()) 