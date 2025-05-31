#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

def check_api_key():
    """检查当前系统中的 OpenAI API 密钥"""
    
    print("🔍 检查 OpenAI API 密钥来源...")
    print("=" * 50)
    
    # 1. 检查 .env 文件
    print("1. 检查 .env 文件:")
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'OPENAI_API_KEY' in content:
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('OPENAI_API_KEY'):
                        key = line.split('=', 1)[1] if '=' in line else ""
                        if key:
                            print(f"   .env 文件中的密钥: {key[:20]}...{key[-10:]}")
                        break
            else:
                print("   .env 文件中未找到 OPENAI_API_KEY")
    except FileNotFoundError:
        print("   .env 文件不存在")
    except Exception as e:
        print(f"   读取 .env 文件时出错: {e}")
    
    # 2. 检查系统环境变量（在加载 .env 之前）
    print("\n2. 检查系统环境变量:")
    sys_env_key = os.environ.get('OPENAI_API_KEY')
    if sys_env_key:
        print(f"   系统环境变量: {sys_env_key[:20]}...{sys_env_key[-10:]}")
    else:
        print("   系统环境变量中未找到 OPENAI_API_KEY")
    
    # 3. 加载 .env 文件后再次检查
    print("\n3. 加载 .env 文件后:")
    load_dotenv()
    final_key = os.getenv('OPENAI_API_KEY')
    if final_key:
        print(f"   最终使用的密钥: {final_key[:20]}...{final_key[-10:]}")
        print(f"   密钥长度: {len(final_key)}")
        
        # 检查是否是以 fluA 结尾的旧密钥
        if final_key.endswith('fluA'):
            print("   ⚠️ 警告: 这是以 'fluA' 结尾的旧密钥!")
        elif final_key.endswith('V6MA'):
            print("   ✅ 这是新的正确密钥!")
        else:
            print(f"   ❓ 密钥结尾: {final_key[-10:]}")
    else:
        print("   未找到任何 OPENAI_API_KEY")

if __name__ == "__main__":
    check_api_key() 