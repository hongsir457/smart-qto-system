#!/usr/bin/env python3
import requests
import json

# API测试配置
BASE_URL = "http://127.0.0.1:8000"
API_V1 = f"{BASE_URL}/api/v1"

# 测试用的JWT token（从日志中获取）
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJvaW4xOTE0QGdhbWlsLmNvbSIsImV4cCI6MTc0ODE2NTA1Mn0.wmK2TpBgvbm0eBgTTsO2rWKYRSUJqcnoJQeLHr4ToWE"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_drawings_api():
    print("开始测试图纸API...")
    
    # 测试1: 不带斜杠的请求
    print("\n1. 测试不带斜杠的请求:")
    try:
        response = requests.get(f"{API_V1}/drawings", headers=headers, params={"page": 1, "size": 10})
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"成功获取数据，图纸数量: {len(data.get('items', []))}")
        else:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"请求异常: {e}")
    
    # 测试2: 带斜杠的请求
    print("\n2. 测试带斜杠的请求:")
    try:
        response = requests.get(f"{API_V1}/drawings/", headers=headers, params={"page": 1, "size": 10})
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"成功获取数据，图纸数量: {len(data.get('items', []))}")
        else:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"请求异常: {e}")
    
    # 测试3: 测试重定向行为
    print("\n3. 测试重定向行为:")
    try:
        response = requests.get(f"{API_V1}/drawings", headers=headers, params={"page": 1, "size": 10}, allow_redirects=False)
        print(f"状态码: {response.status_code}")
        if response.status_code == 307:
            print(f"重定向到: {response.headers.get('Location', 'N/A')}")
        elif response.status_code == 200:
            print("直接返回结果，无重定向")
    except Exception as e:
        print(f"请求异常: {e}")

if __name__ == "__main__":
    test_drawings_api() 