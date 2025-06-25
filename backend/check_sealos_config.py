#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sealos配置检查脚本
"""

def main():
    print("🔍 检查Sealos配置...")
    
    try:
        from app.core.config import settings
        
        print("\n✅ 配置加载成功")
        print("="*50)
        print(f"S3_ENDPOINT:    {settings.S3_ENDPOINT}")
        print(f"S3_BUCKET:      {settings.S3_BUCKET}")
        print(f"S3_REGION:      {settings.S3_REGION}")
        print(f"DATABASE_URL:   {settings.DATABASE_URL[:50]}...")
        print(f"POSTGRES_URL:   {settings.POSTGRES_URL[:50]}...")
        print("="*50)
        
        # 检查是否使用默认值
        if settings.S3_ACCESS_KEY == "":
            print("⚠️  S3_ACCESS_KEY 未配置")
        else:
            print("✅ S3_ACCESS_KEY 已配置")
            
        if settings.S3_SECRET_KEY == "":
            print("⚠️  S3_SECRET_KEY 未配置")
        else:
            print("✅ S3_SECRET_KEY 已配置")
            
        # 检查是否移除了模拟模式
        try:
            from app.services.s3_service import s3_service
            print("✅ S3Service加载成功")
            print(f"   使用端点: {s3_service.endpoint_url}")
            print(f"   存储桶: {s3_service.bucket_name}")
        except Exception as e:
            print(f"❌ S3Service加载失败: {e}")
        
        print("\n🎉 Sealos配置检查完成！")
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")

if __name__ == "__main__":
    main() 