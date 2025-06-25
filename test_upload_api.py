#!/usr/bin/env python3
"""
测试上传API的脚本
"""

import requests
import json

# API配置
BASE_URL = "http://127.0.0.1:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZXhwIjoxNzUwMzk1MTgzfQ.G9I44iFjHA1orWY_P9kx9KGMK3YhwlqWYcBGGhLmBxc"

def test_upload():
    """测试单文件上传"""
    
    # 准备请求头
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    # 准备文件
    files = {
        'file': ('test_upload.txt', open('test_upload.txt', 'rb'), 'text/plain')
    }
    
    try:
        # 发送请求
        response = requests.post(
            f"{BASE_URL}/api/v1/drawings/upload",
            headers=headers,
            files=files
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 上传成功!")
            print(f"图纸ID: {result.get('drawing_id')}")
            print(f"存储方式: {result.get('storage_method')}")
        else:
            print("❌ 上传失败!")
            
    except Exception as e:
        print(f"请求失败: {e}")
    finally:
        files['file'][1].close()

if __name__ == "__main__":
    test_upload() 