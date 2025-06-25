#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单API接口测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

# 设置环境变量
import os
os.environ['PYTHONPATH'] = str(backend_root)

# 导入所需模块
from fastapi.testclient import TestClient
from app.main import app

# 创建测试客户端
client = TestClient(app)

def test_health_check():
    """测试健康检查接口"""
    try:
        response = client.get("/health")
        print(f"健康检查 - 状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_docs():
    """测试文档接口"""
    try:
        response = client.get("/docs")
        print(f"API文档 - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ API文档可访问")
            return True
        else:
            print(f"❌ API文档失败")
            return False
    except Exception as e:
        print(f"❌ API文档异常: {e}")
        return False

def test_openapi():
    """测试OpenAPI规范"""
    try:
        response = client.get("/openapi.json")
        print(f"OpenAPI规范 - 状态码: {response.status_code}")
        if response.status_code == 200:
            spec = response.json()
            paths_count = len(spec.get("paths", {}))
            print(f"✅ OpenAPI规范正常，包含 {paths_count} 个路径")
            return True
        else:
            print("❌ OpenAPI规范失败")
            return False
    except Exception as e:
        print(f"❌ OpenAPI规范异常: {e}")
        return False

def test_api_routes():
    """测试主要API路由"""
    test_routes = [
        ("/api/v1/tasks/stats", "GET"),
        ("/api/v1/tasks/active", "GET"),
        ("/api/v1/chatgpt/status", "GET"),
        ("/api/v1/playground/config", "GET"),
    ]
    
    results = []
    for route, method in test_routes:
        try:
            if method == "GET":
                response = client.get(route)
            elif method == "POST":
                response = client.post(route, json={})
            
            print(f"{route} - 状态码: {response.status_code}")
            
            # 200, 401(未授权), 422(验证错误) 都表示路由存在
            if response.status_code in [200, 401, 422]:
                print(f"✅ {route} 路由可访问")
                results.append(True)
            else:
                print(f"⚠️ {route} 意外状态码: {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ {route} 异常: {e}")
            results.append(False)
    
    return all(results)

def main():
    """主测试函数"""
    print("🚀 开始简单API测试...\n")
    
    tests = [
        ("健康检查", test_health_check),
        ("API文档", test_docs),
        ("OpenAPI规范", test_openapi),
        ("API路由", test_api_routes),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 测试: {test_name}")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
    
    # 总结
    print("\n" + "=" * 40)
    print("📊 测试总结:")
    passed = 0
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    total = len(results)
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有基础API测试通过！")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 