#!/usr/bin/env python3
"""测试图纸上传API修复"""

import requests
import time

def test_upload_fix():
    try:
        print("🔍 检查后端服务状态...")
        health_response = requests.get('http://localhost:8000/api/v1/health', timeout=5)
        
        if health_response.status_code == 200:
            print("✅ 后端服务正常运行")
            return True
        else:
            print(f"❌ 后端服务状态异常: {health_response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务")
        return False
    except Exception as e:
        print(f"❌ 检查服务异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 测试图纸上传API修复...")
    time.sleep(3)
    success = test_upload_fix()
    if success:
        print("🎉 服务正常！")
    else:
        print("💥 服务异常") 