#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision分析修复验证脚本
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_syntax_fixes():
    """测试语法修复是否成功"""
    print("🧪 测试语法修复...")
    
    try:
        # 测试 enhanced_grid_slice_analyzer.py 语法
        import py_compile
        py_compile.compile('app/services/enhanced_grid_slice_analyzer.py', doraise=True)
        print("✅ enhanced_grid_slice_analyzer.py 语法正确")
        
        # 测试 drawing_tasks.py 语法
        py_compile.compile('app/tasks/drawing_tasks.py', doraise=True)
        print("✅ drawing_tasks.py 语法正确")
        
        return True
    except Exception as e:
        print(f"❌ 语法测试失败: {e}")
        return False

def test_imports():
    """测试导入是否成功"""
    print("\n🧪 测试关键导入...")
    
    try:
        # 测试关键模块导入
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        print("✅ EnhancedGridSliceAnalyzer 导入成功")
        
        from app.services.result_merger_service import ResultMergerService
        print("✅ ResultMergerService 导入成功")
        
        from app.tasks.drawing_tasks import process_drawing_celery_task
        print("✅ process_drawing_celery_task 导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        return False

def test_result_merger_instantiation():
    """测试ResultMergerService实例化"""
    print("\n🧪 测试ResultMergerService实例化...")
    
    try:
        from app.services.result_merger_service import ResultMergerService
        
        # 创建实例
        merger_service = ResultMergerService()
        print("✅ ResultMergerService 实例化成功")
        
        # 测试方法存在
        assert hasattr(merger_service, 'merge_vision_analysis_results'), "缺少 merge_vision_analysis_results 方法"
        assert hasattr(merger_service, 'merge_ocr_slice_results'), "缺少 merge_ocr_slice_results 方法"
        print("✅ ResultMergerService 方法验证成功")
        
        return True
    except Exception as e:
        print(f"❌ ResultMergerService 测试失败: {e}")
        return False

def test_enhanced_analyzer_instantiation():
    """测试EnhancedGridSliceAnalyzer实例化"""
    print("\n🧪 测试EnhancedGridSliceAnalyzer实例化...")
    
    try:
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        # 创建实例
        analyzer = EnhancedGridSliceAnalyzer()
        print("✅ EnhancedGridSliceAnalyzer 实例化成功")
        
        # 测试关键方法存在
        assert hasattr(analyzer, 'analyze_drawing_with_dual_track'), "缺少 analyze_drawing_with_dual_track 方法"
        assert hasattr(analyzer, '_build_global_overview_prompt'), "缺少 _build_global_overview_prompt 方法"
        print("✅ EnhancedGridSliceAnalyzer 方法验证成功")
        
        return True
    except Exception as e:
        print(f"❌ EnhancedGridSliceAnalyzer 测试失败: {e}")
        return False

def test_f_string_fix():
    """测试f-string修复是否生效"""
    print("\n🧪 测试f-string修复...")
    
    try:
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        analyzer = EnhancedGridSliceAnalyzer()
        
        # 测试 _build_global_overview_prompt 方法
        test_drawing_info = {
            'drawing_name': '测试图纸.dwg',
            'drawing_type': '建筑平面图'
        }
        test_ocr_text = "KL1 框架梁 C30 混凝土" * 1000  # 创建超过4000字符的文本
        
        prompt = analyzer._build_global_overview_prompt(test_ocr_text, test_drawing_info)
        print("✅ _build_global_overview_prompt 方法执行成功")
        
        # 验证截断逻辑正常工作
        assert '...(文本过长，已截断)' in prompt, "截断逻辑未正常工作"
        print("✅ 文本截断逻辑正常工作")
        
        return True
    except Exception as e:
        print(f"❌ f-string 测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始Vision分析修复验证\n")
    
    tests = [
        ("语法修复", test_syntax_fixes),
        ("导入测试", test_imports), 
        ("ResultMergerService实例化", test_result_merger_instantiation),
        ("EnhancedGridSliceAnalyzer实例化", test_enhanced_analyzer_instantiation),
        ("f-string修复", test_f_string_fix)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"📋 执行测试: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过\n")
            else:
                print(f"❌ {test_name} 失败\n")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}\n")
    
    print("="*60)
    print(f"🎯 测试结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！Vision分析修复成功！")
        print("\n修复内容总结:")
        print("1. ✅ 修复了 enhanced_grid_slice_analyzer.py 第574行的f-string反斜杠错误")
        print("2. ✅ 在 drawing_tasks.py 中添加了 ResultMergerService 导入")
        print("3. ✅ 在 Vision结果合并阶段实例化了 merger_service")
        print("4. ✅ 验证了所有关键组件可以正常导入和实例化")
        print("\n现在Vision分析应该可以正常工作，不再出现以下错误:")
        print("   - f-string expression part cannot include a backslash")
        print("   - name 'merger_service' is not defined")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        return False

if __name__ == "__main__":
    main() 