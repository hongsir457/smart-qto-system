import requests
import json

def test_api_endpoints():
    """测试API端点可访问性"""
    base_url = "http://localhost:8000"
    
    print("开始测试API端点...")
    
    # 1. 测试根路径
    try:
        response = requests.get(f"{base_url}/")
        print(f"根路径 (/): {response.status_code}")
    except Exception as e:
        print(f"根路径测试失败: {e}")
    
    # 2. 测试文档页面
    try:
        response = requests.get(f"{base_url}/docs")
        print(f"文档页面 (/docs): {response.status_code}")
    except Exception as e:
        print(f"文档页面测试失败: {e}")
    
    # 3. 测试API v1路径
    try:
        response = requests.get(f"{base_url}/api/v1")
        print(f"API v1 (/api/v1): {response.status_code}")
    except Exception as e:
        print(f"API v1测试失败: {e}")
    
    # 4. 测试图纸列表端点（需要认证，但可以测试路由是否存在）
    try:
        response = requests.get(f"{base_url}/api/v1/drawings/")
        print(f"图纸列表 (/api/v1/drawings/): {response.status_code}")
        if response.status_code == 401:
            print("  - 端点存在但需要认证（正常）")
        elif response.status_code == 404:
            print("  - 端点不存在（问题）")
    except Exception as e:
        print(f"图纸列表测试失败: {e}")
    
    # 5. 测试OCR端点（需要认证，但可以测试路由是否存在）
    try:
        response = requests.post(f"{base_url}/api/v1/drawings/1/ocr")
        print(f"OCR端点 (/api/v1/drawings/1/ocr): {response.status_code}")
        if response.status_code == 401:
            print("  - 端点存在但需要认证（正常）")
        elif response.status_code == 404:
            print("  - 端点不存在（问题）")
    except Exception as e:
        print(f"OCR端点测试失败: {e}")
    
    # 6. 测试构件检测端点
    try:
        response = requests.post(f"{base_url}/api/v1/drawings/1/detect-components")
        print(f"构件检测端点 (/api/v1/drawings/1/detect-components): {response.status_code}")
        if response.status_code == 401:
            print("  - 端点存在但需要认证（正常）")
        elif response.status_code == 404:
            print("  - 端点不存在（问题）")
    except Exception as e:
        print(f"构件检测端点测试失败: {e}")

if __name__ == "__main__":
    test_api_endpoints() 