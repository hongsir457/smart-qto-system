#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('../.env')

# 获取 API 密钥
key = os.getenv('OPENAI_API_KEY')

if key:
    print(f"✅ 成功读取 API 密钥")
    print(f"🔑 密钥长度: {len(key)} 字符")
    print(f"📝 密钥前20字符: {key[:20]}")
    print(f"📝 密钥后20字符: {key[-20:]}")
    print(f"🔍 完整密钥: {key}")
else:
    print("❌ 未能读取到 API 密钥") 