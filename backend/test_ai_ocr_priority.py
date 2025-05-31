#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI OCR优先使用测试脚本
验证系统是否默认使用AI OCR
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.services.drawing import extract_text
from app.config.ocr_config import OCRConfig

def test_ai_ocr_priority():
    """测试AI OCR优先使用配置"""
    print("🤖 AI OCR优先使用测试")
    print("=" * 60)
    
    # 1. 显示当前配置
    print("\n📋 当前OCR配置状态:")
    OCRConfig.print_current_config()
    
    # 2. 测试默认行为
    test_image = "complex_building_plan.png"
    
    if not os.path.exists(test_image):
        print(f"\n❌ 测试图片不存在: {test_image}")
        return
    
    print(f"\n🔍 测试图片: {test_image}")
    print("-" * 40)
    
    # 3. 测试默认调用（应该使用AI OCR）
    print("\n🧪 测试1: 默认调用extract_text()（应该使用AI OCR）")
    try:
        result = extract_text(test_image)  # 不指定参数，使用默认值
        
        if isinstance(result, dict):
            if "provider" in result:
                print(f"✅ 成功使用AI OCR")
                print(f"   - 服务提供商: {result['provider']}")
                print(f"   - 模型: {result.get('model', 'unknown')}")
                print(f"   - 识别字符数: {len(result.get('text', ''))}")
                print(f"   - Token消耗: {result.get('tokens_used', 'unknown')}")
            elif "text" in result:
                print(f"⚠️  使用了传统OCR（可能是AI失败后的降级）")
                print(f"   - 识别字符数: {len(result.get('text', ''))}")
            else:
                print(f"❌ 识别失败: {result}")
        else:
            print(f"❌ 返回格式异常: {type(result)}")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    
    # 4. 测试显式指定AI OCR
    print("\n🧪 测试2: 显式指定use_ai=True")
    try:
        result = extract_text(test_image, use_ai=True, ai_provider="auto")
        
        if isinstance(result, dict) and "provider" in result:
            print(f"✅ 显式AI OCR成功")
            print(f"   - 服务提供商: {result['provider']}")
        else:
            print(f"⚠️  显式AI OCR失败或降级")
            
    except Exception as e:
        print(f"❌ 显式AI OCR测试失败: {str(e)}")
    
    # 5. 测试传统OCR作为对比
    print("\n🧪 测试3: 显式指定use_ai=False（传统OCR）")
    try:
        result = extract_text(test_image, use_ai=False)
        
        if isinstance(result, dict) and "text" in result and "provider" not in result:
            print(f"✅ 传统OCR成功")
            print(f"   - 识别字符数: {len(result.get('text', ''))}")
        else:
            print(f"⚠️  传统OCR结果异常")
            
    except Exception as e:
        print(f"❌ 传统OCR测试失败: {str(e)}")
    
    # 6. 总结
    print("\n📊 测试总结:")
    strategy = OCRConfig.get_ocr_strategy()
    
    if strategy["mode"] == "ai_first":
        print("✅ 系统已正确配置为AI OCR优先")
        print(f"   - 默认AI服务商: {strategy['ai_provider']}")
        print(f"   - 降级策略: {strategy['fallback']}")
    else:
        print("⚠️  系统当前使用传统OCR")
        print("   - 可能的原因: AI API密钥未配置")
    
    print("\n💡 使用建议:")
    print("   - 现在系统默认使用AI OCR，无需额外配置")
    print("   - 如需使用传统OCR，请显式指定 use_ai=False")
    print("   - AI失败时会自动降级到传统OCR，确保服务可用")

def test_api_keys():
    """测试API密钥配置"""
    print("\n🔑 API密钥配置检查:")
    print("-" * 30)
    
    api_keys = [
        ("OpenAI", "OPENAI_API_KEY"),
        ("Claude", "CLAUDE_API_KEY"),
        ("百度", "BAIDU_API_KEY"),
        ("通义千问", "QWEN_API_KEY"),
    ]
    
    available_count = 0
    for name, env_var in api_keys:
        value = os.getenv(env_var)
        if value:
            # 显示前缀和后缀，中间用*代替
            masked = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else f"{value[:5]}***"
            print(f"✅ {name}: {masked}")
            available_count += 1
        else:
            print(f"❌ {name}: 未配置")
    
    print(f"\n📊 可用AI服务数量: {available_count}/4")
    
    if available_count == 0:
        print("⚠️  警告: 没有配置任何AI服务API密钥")
        print("   系统将只能使用传统OCR")
    elif available_count >= 1:
        print("✅ 至少有一个AI服务可用，系统可以使用AI OCR")

if __name__ == "__main__":
    try:
        test_api_keys()
        test_ai_ocr_priority()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc() 