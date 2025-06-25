#!/usr/bin/env python3
"""测试图纸上传API的await修复"""

import requests
from io import BytesIO
from PIL import Image

def create_test_image():
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

def test_upload_fix():
    print("🧪 测试图纸上传API await修复...")
    
    try:
        # 获取token
        auth_response = requests.post(
            'http://localhost:8000/api/v1/auth/test-login',
            json={"user_id": 2},
            timeout=10
        )
        
        if auth_response.status_code != 200:
            print(f"❌ 获取token失败: {auth_response.status_code}")
            return False
        
        token = auth_response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        print("✅ Token获取成功")
        
        # 创建测试图片
        test_image_data = create_test_image()
        files = {'file': ('test_await_fix.png', test_image_data, 'image/png')}
        
        # 测试上传
        upload_response = requests.post(
            'http://localhost:8000/api/v1/drawings/upload',
            files=files,
            headers=headers,
            timeout=30
        )
        
        print(f"📋 上传响应状态码: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            print("✅ 上传成功！await修复生效")
            result = upload_response.json()
            print(f"📋 图纸ID: {result.get('drawing_id')}")
            print(f"📋 任务ID: {result.get('task_id')}")
            return True
        else:
            print(f"❌ 上传失败: {upload_response.status_code}")
            print(f"错误: {upload_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

if __name__ == "__main__":
    print("🎯 图纸上传API - await修复验证测试")
    success = test_upload_fix()
    if success:
        print("🎉 测试通过！await修复成功！")
    else:
        print("💥 测试失败，需要进一步检查") 