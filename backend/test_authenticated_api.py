import requests
import json

def test_authenticated_api():
    """测试需要认证的API端点"""
    base_url = "http://localhost:8000"
    
    print("开始测试需要认证的API端点...")
    
    # 1. 首先尝试注册一个测试用户（如果不存在）
    test_user = {
        "username": "test_user",
        "email": "test@test.com",
        "password": "test123456"
    }
    
    # 2. 尝试登录获取token
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    
    # 使用form data格式
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print(f"登录请求状态: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            print(f"登录成功，获取到token: {access_token[:20]}...")
            
            # 设置认证头
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # 3. 测试需要认证的端点
            # 测试图纸列表
            response = requests.get(f"{base_url}/api/v1/drawings/", headers=headers)
            print(f"图纸列表 (已认证): {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  - 总数: {data.get('total', 0)}")
            
            # 测试OCR端点（使用不存在的drawing_id，但应该返回404而不是401）
            response = requests.post(f"{base_url}/api/v1/drawings/999/ocr", headers=headers)
            print(f"OCR端点 (已认证): {response.status_code}")
            if response.status_code == 404:
                print("  - 图纸不存在（正常，证明端点工作）")
            elif response.status_code == 401:
                print("  - 仍然需要认证（异常）")
            
            # 测试构件检测端点
            response = requests.post(f"{base_url}/api/v1/drawings/999/detect-components", headers=headers)
            print(f"构件检测端点 (已认证): {response.status_code}")
            if response.status_code == 404:
                print("  - 图纸不存在（正常，证明端点工作）")
            elif response.status_code == 401:
                print("  - 仍然需要认证（异常）")
                
        elif response.status_code == 400:
            print("登录失败，可能是用户不存在或密码错误")
            # 尝试注册用户
            print("尝试注册新用户...")
            response = requests.post(f"{base_url}/api/v1/auth/register", json=test_user)
            print(f"注册状态: {response.status_code}")
            
            if response.status_code == 200:
                print("注册成功，重新尝试登录...")
                response = requests.post(
                    f"{base_url}/api/v1/auth/login",
                    data=login_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    print(f"登录成功，获取到token: {access_token[:20]}...")
                    headers = {"Authorization": f"Bearer {access_token}"}
                    
                    # 测试认证端点
                    response = requests.get(f"{base_url}/api/v1/drawings/", headers=headers)
                    print(f"图纸列表 (已认证): {response.status_code}")
        else:
            print(f"登录失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_authenticated_api() 