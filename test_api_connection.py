#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import json
from dotenv import load_dotenv

def test_api_connection():
    """测试 API 连接"""
    
    # 加载环境变量
    load_dotenv()
    
    print("🧪 测试 OpenAI API 连接...")
    print("=" * 50)
    
    # 获取 API 密钥
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 未找到 OPENAI_API_KEY 环境变量")
        return False
    
    print(f"✅ API 密钥: {api_key[:20]}...{api_key[-10:]}")
    print(f"✅ 密钥长度: {len(api_key)}")
    
    # 测试 API 调用
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'chatgpt-4o-latest',
        'messages': [
            {
                'role': 'user',
                'content': '你好，请回复"API连接成功"'
            }
        ],
        'max_tokens': 50
    }
    
    try:
        print("\n🔄 发送测试请求...")
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print(f"✅ API 响应成功: {message}")
            return True
        else:
            print(f"❌ API 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_backend_api():
    """测试后端 API"""
    
    print("\n🧪 测试后端 API...")
    print("=" * 50)
    
    try:
        # 测试后端健康检查
        response = requests.get('http://localhost:8000/health', timeout=10)
        print(f"📊 后端健康检查状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 后端服务正常运行")
            return True
        else:
            print(f"❌ 后端服务异常: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 后端连接失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始 API 连接测试...")
    
    # 测试 OpenAI API
    openai_ok = test_api_connection()
    
    # 测试后端 API
    backend_ok = test_backend_api()
    
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    print(f"   OpenAI API: {'✅ 正常' if openai_ok else '❌ 异常'}")
    print(f"   后端服务: {'✅ 正常' if backend_ok else '❌ 异常'}")
    
    if openai_ok and backend_ok:
        print("\n🎉 所有测试通过！系统已准备就绪。")
    else:
        print("\n⚠️ 部分测试失败，请检查配置。") 