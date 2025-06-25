#!/usr/bin/env python3
"""
GPT-4o-2024-11-20模型配置验证脚本
验证系统是否正确配置了用户指定的模型版本
"""
import os
import json
from app.services.ai_processing.gpt_analyzer import GPTAnalyzer

def check_model_availability():
    """检查模型可用性"""
    print("🔍 模型权限验证")
    print("=" * 50)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ 未设置OPENAI_API_KEY环境变量")
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # 获取可用模型列表
        models_response = client.models.list()
        available_models = [model.id for model in models_response.data]
        
        print(f"📋 您的API密钥可访问 {len(available_models)} 个模型")
        
        # 检查关键模型
        target_models = [
            "gpt-4o-2024-11-20",
            "chatgpt-4o-latest", 
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4"
        ]
        
        available_targets = []
        for model in target_models:
            if model in available_models:
                available_targets.append(model)
                print(f"✅ {model} - 可用")
            else:
                print(f"❌ {model} - 不可用")
        
        print(f"\n🎯 推荐使用模型: gpt-4o-2024-11-20")
        
        if "gpt-4o-2024-11-20" in available_targets:
            print("✅ 您的密钥支持推荐模型")
            return True
        elif "chatgpt-4o-latest" in available_targets:
            print("⚠️  推荐模型不可用，将使用 chatgpt-4o-latest")
            return True
        else:
            print("❌ 您的密钥不支持GPT-4o系列模型")
            return False
            
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        return False

def test_analyzer_initialization():
    """测试分析器初始化"""
    print("\n🧪 分析器初始化测试")
    print("=" * 50)
    
    try:
        analyzer = GPTAnalyzer()
        
        print(f"🤖 配置的模型: {analyzer.model}")
        print(f"🔗 AI功能: {'启用' if analyzer.ai_enabled else '未启用'}")
        print(f"👁️  视觉功能: {'启用' if analyzer.vision_enabled else '未启用'}")
        
        if analyzer.ai_enabled:
            print("✅ 分析器初始化成功")
            return True
        else:
            print("❌ 分析器初始化失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_model_response():
    """测试模型响应"""
    print("\n💬 模型响应测试")
    print("=" * 50)
    
    try:
        analyzer = GPTAnalyzer()
        
        if not analyzer.ai_enabled:
            print("❌ AI功能未启用，跳过响应测试")
            return False
        
        # 创建测试用OCR数据
        test_ocr = {
            'success': True,
            'recognized_texts': [
                {'text': 'KZ1', 'confidence': 0.95, 'bbox': [100, 150, 140, 170]},
                {'text': '400×600', 'confidence': 0.92, 'bbox': [200, 200, 280, 220]}
            ]
        }
        
        print(f"🔧 使用模型: {analyzer.model}")
        print("📝 发送测试分析请求...")
        
        result = analyzer.analyze_components(test_ocr)
        
        if result.get('success'):
            components = result.get('components', [])
            mode = result.get('analysis_mode', 'unknown')
            model = result.get('model_used', analyzer.model)
            
            print(f"✅ 分析成功")
            print(f"📊 识别构件: {len(components)} 个")
            print(f"🔧 分析模式: {mode}")
            print(f"🤖 使用模型: {model}")
            
            return True
        else:
            print(f"❌ 分析失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ 响应测试失败: {str(e)}")
        return False

def show_configuration_summary():
    """显示配置摘要"""
    print("\n📋 配置摘要")
    print("=" * 50)
    
    analyzer = GPTAnalyzer()
    
    config = {
        "模型版本": analyzer.model,
        "AI功能": "启用" if analyzer.ai_enabled else "未启用",
        "视觉分析": "启用" if analyzer.vision_enabled else "未启用",
        "API密钥": "已配置" if os.getenv('OPENAI_API_KEY') else "未配置"
    }
    
    for key, value in config.items():
        status = "✅" if value in ["启用", "已配置", analyzer.model] else "❌"
        print(f"{status} {key}: {value}")
    
    print(f"\n🎯 系统状态: ", end="")
    if analyzer.ai_enabled and analyzer.vision_enabled:
        print("🟢 完全就绪 - GPT-4o多模态分析可用")
    elif analyzer.ai_enabled:
        print("🟡 部分就绪 - 仅文本分析可用")
    else:
        print("🔴 未就绪 - 仅规则引擎可用")

def main():
    """主函数"""
    print("🚀 GPT-4o-2024-11-20 模型配置验证")
    print("=" * 60)
    
    # 步骤1: 检查模型可用性
    if not check_model_availability():
        print("\n❌ 模型可用性检查失败")
        return
    
    # 步骤2: 测试分析器初始化
    if not test_analyzer_initialization():
        print("\n❌ 分析器初始化失败")
        return
    
    # 步骤3: 测试模型响应
    if not test_model_response():
        print("\n⚠️  模型响应测试失败，但基本功能可用")
    
    # 步骤4: 显示配置摘要
    show_configuration_summary()
    
    print(f"\n🎉 验证完成！")
    print("=" * 60)
    print("💡 接下来您可以:")
    print("   • 运行演示: python demo_ai_system.py")
    print("   • 功能测试: python test_multimodal_ai.py")
    print("   • 一键配置: python setup_gpt4o.py")

if __name__ == "__main__":
    main() 