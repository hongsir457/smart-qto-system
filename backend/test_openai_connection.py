#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI连接测试
"""

import sys
sys.path.append('.')

def test_openai_connection():
    """测试OpenAI连接"""
    print("🔗 测试OpenAI连接")
    print("=" * 50)
    
    try:
        from app.core.config import settings
        
        # 检查配置
        if not settings.OPENAI_API_KEY:
            print("❌ OpenAI API Key未配置")
            return False
        
        api_key_preview = "sk-" + "*" * 20 + settings.OPENAI_API_KEY[-8:]
        print(f"✅ API Key已配置: {api_key_preview}")
        print(f"📝 模型: {settings.OPENAI_MODEL}")
        print(f"🌡️ 温度: {settings.OPENAI_TEMPERATURE}")
        print(f"📏 最大Token: {settings.OPENAI_MAX_TOKENS}")
        
        # 测试OpenAI客户端初始化
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            print(f"✅ OpenAI客户端初始化成功")
        except Exception as client_error:
            print(f"❌ OpenAI客户端初始化失败: {client_error}")
            return False
        
        # 测试简单的API调用
        try:
            print(f"\n🧪 测试简单API调用...")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # 使用便宜的模型测试
                messages=[
                    {"role": "user", "content": "Hello, 请回复'连接成功'"}
                ],
                max_tokens=10,
                timeout=30
            )
            
            if response.choices[0].message.content:
                print(f"✅ API调用成功")
                print(f"📝 响应: {response.choices[0].message.content}")
                return True
            else:
                print(f"⚠️ API调用成功但响应为空")
                return False
                
        except Exception as api_error:
            print(f"❌ API调用失败: {api_error}")
            print(f"错误类型: {type(api_error).__name__}")
            
            # 分析常见错误
            error_str = str(api_error).lower()
            if "connection" in error_str:
                print(f"💡 这是网络连接问题，可能的解决方案:")
                print(f"   • 检查网络连接")
                print(f"   • 检查防火墙设置")
                print(f"   • 尝试使用代理")
            elif "authentication" in error_str or "401" in error_str:
                print(f"💡 这是认证问题，请检查API Key是否正确")
            elif "rate limit" in error_str or "429" in error_str:
                print(f"💡 这是频率限制问题，请稍后再试")
            elif "timeout" in error_str:
                print(f"💡 这是超时问题，请检查网络稳定性")
            
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_ai_analyzer_service():
    """测试AI分析服务"""
    print(f"\n🤖 测试AI分析服务")
    print("=" * 50)
    
    try:
        from app.services.ai_analyzer import AIAnalyzerService
        
        ai_service = AIAnalyzerService()
        
        print(f"服务可用性: {'✅ 可用' if ai_service.is_available() else '❌ 不可用'}")
        print(f"客户端类型: {type(ai_service.client).__name__ if ai_service.client else '未初始化'}")
        
        if ai_service.is_available():
            print(f"✅ AI分析服务已就绪")
        else:
            print(f"❌ AI分析服务不可用")
            
        return ai_service.is_available()
        
    except Exception as e:
        print(f"❌ AI服务测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始OpenAI连接诊断")
    
    # 测试基础连接
    basic_ok = test_openai_connection()
    
    # 测试AI服务
    service_ok = test_ai_analyzer_service()
    
    print(f"\n📊 诊断结果:")
    print(f"基础连接: {'✅ 正常' if basic_ok else '❌ 异常'}")
    print(f"AI服务: {'✅ 正常' if service_ok else '❌ 异常'}")
    
    if basic_ok and service_ok:
        print(f"\n🎉 OpenAI连接正常，可以进行LLM分析!")
    else:
        print(f"\n⚠️ 存在连接问题，需要修复后才能进行真实的LLM分析")
        print(f"📝 当前的LLM结果可能是缓存的测试数据或降级响应") 