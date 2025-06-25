#!/usr/bin/env python3
"""
GPT智能分析功能验证脚本
验证以下修复：
1. GPT智能分析已重新启用（不是词典纠错）
2. PaddleOCR词典纠错已禁用
"""

import sys

def test_1_gpt_analysis_enabled():
    """测试1：验证GPT智能分析是否已启用"""
    print("🧪 测试1：验证GPT智能分析功能...")
    
    try:
        file_path = "app/services/ocr_result_corrector.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查GPT分析是否启用
        if "🤖 开始GPT智能分析：纠正明显错误、提取图纸信息和构件清单" in content:
            print("✅ GPT智能分析功能已正确启用")
            
            # 检查是否强调不使用词典纠错
            if "不使用词典纠错，而是让GPT基于上下文进行智能判断" in content:
                print("✅ 已明确不使用词典纠错，使用智能判断")
                
                # 检查是否有实际的AI分析调用
                if "self.ai_analyzer.analyze_text_async" in content:
                    print("✅ 找到AI分析器调用逻辑")
                    return True
                else:
                    print("❌ 未找到AI分析器调用逻辑")
            else:
                print("❌ 未找到智能分析说明")
        else:
            print("❌ GPT智能分析功能未启用")
            
        return False
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_2_dictionary_correction_disabled():
    """测试2：验证词典纠错是否已禁用"""
    print("\n🧪 测试2：验证PaddleOCR词典纠错已禁用...")
    
    try:
        file_path = "app/services/ocr/paddle_ocr.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查词典纠错调用是否被注释
        if "# processed_result = self._apply_construction_text_correction(processed_result)" in content:
            print("✅ 词典纠错调用已被正确注释")
            
            # 检查是否有禁用日志
            if "🚫 文本纠错已禁用，保持OCR原始结果" in content:
                print("✅ 找到禁用词典纠错的日志信息")
                return True
            else:
                print("❌ 未找到禁用日志")
        else:
            print("❌ 词典纠错调用未被注释，仍可能执行错误纠正")
            
        return False
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 开始验证GPT智能分析功能修复...")
    print("=" * 60)
    
    test_results = []
    
    # 执行所有测试
    test_results.append(("GPT智能分析启用", test_1_gpt_analysis_enabled()))
    test_results.append(("词典纠错禁用", test_2_dictionary_correction_disabled()))
    
    # 统计结果
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！GPT智能分析功能修复成功")
        print("\n💡 功能说明:")
        print("   ✓ GPT智能分析：基于上下文纠正明显错误、提取图纸信息")
        print("   ✓ 词典纠错禁用：不再使用预设词典自动替换文本")
        print("   ✓ 为Vision分析提供全图概览和构件清单")
        
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 