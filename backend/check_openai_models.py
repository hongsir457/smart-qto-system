#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查OpenAI API配置和可用模型
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_openai_config():
    """检查OpenAI配置和可用模型"""
    print('🔍 OpenAI配置检查')
    print('=' * 40)
    
    try:
        import openai
        from app.core.config import settings
        
        print(f'API Key状态: {"已配置" if settings.OPENAI_API_KEY else "未配置"}')
        if settings.OPENAI_API_KEY:
            print(f'API Key长度: {len(settings.OPENAI_API_KEY)}')
            print(f'API Key前缀: {settings.OPENAI_API_KEY[:20]}...')
            print(f'配置的模型: {settings.OPENAI_MODEL}')
            
            # 测试API连接
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                
                # 列出可用模型
                print('\n🔍 检查可用模型...')
                models = client.models.list()
                available_models = [model.id for model in models.data]
                
                gpt4_models = [model for model in available_models if 'gpt-4' in model.lower()]
                print(f'可用的GPT-4系列模型: {gpt4_models[:10]}')  # 只显示前10个
                
                # 检查目标模型
                target_model = settings.OPENAI_MODEL
                print(f'\n目标模型 {target_model} 是否可用: {"✅" if target_model in available_models else "❌"}')
                
                # 如果目标模型不可用，推荐替代模型
                if target_model not in available_models:
                    print('\n🔍 推荐的替代模型:')
                    for model in gpt4_models[:5]:
                        print(f'   - {model}')
                        
                # 测试简单API调用
                print('\n🧪 测试API调用...')
                test_response = client.chat.completions.create(
                    model=settings.OPENAI_MODEL,  # 使用配置中的模型
                    messages=[{"role": "user", "content": "Hello, test"}],
                    max_tokens=10
                )
                print("✅ API调用成功")
                
                return True
                
            except Exception as e:
                print(f'❌ API连接失败: {e}')
                print(f'错误类型: {type(e).__name__}')
                return False
        else:
            print('❌ OpenAI API Key未配置')
            return False
            
    except ImportError as e:
        print(f'❌ 导入错误: {e}')
        return False

if __name__ == "__main__":
    success = check_openai_config()
    sys.exit(0 if success else 1) 