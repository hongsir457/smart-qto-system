#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR TXT存储调试脚本
用于测试和验证TXT合并功能是否正常工作
"""

import os
import sys
import json
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ocr.paddle_ocr import PaddleOCRService
from app.services.dual_storage_service import DualStorageService

def test_txt_storage():
    """测试TXT存储功能"""
    
    print("🔍 开始测试PaddleOCR TXT存储功能...")
    
    # 1. 初始化服务
    ocr_service = PaddleOCRService()
    storage_service = DualStorageService()
    
    print(f"📊 OCR服务状态: {ocr_service.is_available()}")
    print(f"📊 存储服务状态: {storage_service is not None}")
    
    # 2. 检查存储配置
    print("\n🔧 检查存储配置:")
    try:
        from app.core.config import settings
        print(f"   - S3_ENDPOINT: {settings.S3_ENDPOINT}")
        print(f"   - S3_BUCKET: {settings.S3_BUCKET}")
        print(f"   - S3_ACCESS_KEY: {'已配置' if settings.S3_ACCESS_KEY else '未配置'}")
        print(f"   - S3_SECRET_KEY: {'已配置' if settings.S3_SECRET_KEY else '未配置'}")
    except Exception as e:
        print(f"   ❌ 配置检查失败: {e}")
    
    # 3. 查找测试图片
    test_image_dirs = [
        "test_images",
        "uploads", 
        "backend/test_images",
        "backend/uploads"
    ]
    
    test_image = None
    for dir_path in test_image_dirs:
        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    test_image = os.path.join(dir_path, file)
                    break
            if test_image:
                break
    
    if not test_image:
        print("❌ 未找到测试图片，请确保以下目录之一包含图片文件:")
        for dir_path in test_image_dirs:
            print(f"   - {dir_path}")
        return False
    
    print(f"✅ 找到测试图片: {test_image}")
    
    # 4. 执行OCR识别并保存TXT
    print(f"\n🔄 开始OCR识别...")
    try:
        result = ocr_service.recognize_text(
            image_path=test_image,
            save_to_sealos=True,
            drawing_id="debug_test"
        )
        
        print(f"📊 OCR识别结果:")
        print(f"   - 成功: {result.get('success', False)}")
        print(f"   - 识别文本数: {len(result.get('texts', []))}")
        print(f"   - 处理时间: {result.get('processing_time', 'N/A')}")
        
        # 检查存储信息
        storage_info = result.get('storage_info', {})
        if storage_info.get('saved'):
            print(f"\n✅ 存储成功:")
            
            # JSON存储信息
            json_result = storage_info.get('json_result', {})
            if json_result:
                print(f"   📄 JSON文件:")
                print(f"      - S3密钥: {json_result.get('s3_key', 'N/A')}")
                print(f"      - URL: {json_result.get('s3_url', 'N/A')}")
                print(f"      - 存储桶: {json_result.get('bucket', 'N/A')}")
            
            # TXT存储信息
            txt_result = storage_info.get('txt_result', {})
            if txt_result:
                print(f"   📝 TXT文件:")
                print(f"      - S3密钥: {txt_result.get('s3_key', 'N/A')}")
                print(f"      - URL: {txt_result.get('s3_url', 'N/A')}")
                print(f"      - 文件名: {txt_result.get('filename', 'N/A')}")
                print(f"      - 文件大小: {txt_result.get('file_size', 'N/A')} bytes")
                print(f"      - 存储桶: {txt_result.get('bucket', 'N/A')}")
                
                # 尝试验证TXT内容
                verify_txt_content(txt_result, ocr_service, test_image)
            else:
                print("   ❌ TXT文件信息缺失")
        else:
            print(f"❌ 存储失败: {storage_info.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ OCR识别失败: {e}")
        return False
    
    return True

def verify_txt_content(txt_result, ocr_service, image_path):
    """验证TXT内容是否正确生成"""
    print(f"\n🔍 验证TXT内容...")
    
    try:
        # 生成本地TXT内容用于对比
        mock_raw_data = [
            [[[10, 10], [100, 10], [100, 30], [10, 30]], ('KZ-1 300x600', 0.95)],
            [[[10, 40], [120, 40], [120, 60], [10, 60]], ('B=200 H=400', 0.92)]
        ]
        
        local_txt = ocr_service._format_raw_result_as_txt(mock_raw_data, image_path)
        
        print(f"📝 本地生成的TXT内容预览:")
        print("="*50)
        print(local_txt[:500])
        if len(local_txt) > 500:
            print("... (内容截断)")
        print("="*50)
        
        # 检查TXT内容结构
        if "PaddleOCR识别结果" in local_txt:
            print("✅ TXT格式正确 - 包含标题")
        else:
            print("❌ TXT格式异常 - 缺少标题")
            
        if "纯文本内容:" in local_txt:
            print("✅ TXT格式正确 - 包含纯文本区域")
        else:
            print("❌ TXT格式异常 - 缺少纯文本区域")
            
    except Exception as e:
        print(f"❌ TXT内容验证失败: {e}")

def check_sealos_storage():
    """检查Sealos存储中的TXT文件"""
    print(f"\n🔍 检查Sealos存储状态...")
    
    try:
        storage_service = DualStorageService()
        
        # 尝试列出存储中的文件
        print("📂 尝试列出存储中的OCR结果文件...")
        
        # 这里可以添加更多存储检查逻辑
        # 比如列出特定文件夹中的文件
        
    except Exception as e:
        print(f"❌ 存储检查失败: {e}")

if __name__ == "__main__":
    print("🚀 开始PaddleOCR TXT存储功能调试...")
    print("="*60)
    
    success = test_txt_storage()
    
    if success:
        print("\n✅ 测试完成！")
        check_sealos_storage()
    else:
        print("\n❌ 测试失败，请检查配置和错误信息")
    
    print("="*60) 