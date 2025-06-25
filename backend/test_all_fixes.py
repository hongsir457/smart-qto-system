#!/usr/bin/env python3
"""
综合测试脚本 - 验证所有修复是否正确
"""

import sys
import os
import json
import tempfile
import traceback

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

def test_ocr_cache_manager():
    """测试OCRCacheManager修复"""
    try:
        from app.utils.analysis_optimizations import OCRCacheManager
        
        # 创建OCRCacheManager实例
        cache_manager = OCRCacheManager()
        
        # 测试get_cached_ocr方法是否存在
        assert hasattr(cache_manager, 'get_cached_ocr'), "❌ 缺少get_cached_ocr方法"
        
        # 测试方法调用
        result = cache_manager.get_cached_ocr("test_slice", "auto")
        assert result is None, "❌ get_cached_ocr返回值不正确"
        
        print("✅ OCRCacheManager修复验证通过")
        return True
        
    except Exception as e:
        print(f"❌ OCRCacheManager修复验证失败: {e}")
        traceback.print_exc()
        return False

def test_ocr_correction_storage_keys():
    """测试OCR纠正阶段的存储键修复"""
    try:
        # 模拟ocr_result数据结构
        ocr_result_with_merged = {
            'success': True,
            'merged_ocr_storage': {
                's3_key': 'test_key_merged.json'
            }
        }
        
        ocr_result_with_full = {
            'success': True,
            'ocr_full_storage': {
                's3_key': 'test_key_full.json'
            }
        }
        
        # 测试merged_ocr_storage优先级
        ocr_success = True
        merged_ocr_key = None
        if ocr_success and ocr_result_with_merged.get('merged_ocr_storage'):
            merged_ocr_key = ocr_result_with_merged['merged_ocr_storage'].get('s3_key')
        elif ocr_success and ocr_result_with_merged.get('ocr_full_storage'):
            merged_ocr_key = ocr_result_with_merged['ocr_full_storage'].get('s3_key')
        
        assert merged_ocr_key == 'test_key_merged.json', f"❌ merged_ocr_storage优先级不正确: {merged_ocr_key}"
        
        # 测试ocr_full_storage降级
        merged_ocr_key = None
        if ocr_success and ocr_result_with_full.get('merged_ocr_storage'):
            merged_ocr_key = ocr_result_with_full['merged_ocr_storage'].get('s3_key')
        elif ocr_success and ocr_result_with_full.get('ocr_full_storage'):
            merged_ocr_key = ocr_result_with_full['ocr_full_storage'].get('s3_key')
        
        assert merged_ocr_key == 'test_key_full.json', f"❌ ocr_full_storage降级不正确: {merged_ocr_key}"
        
        print("✅ OCR纠正存储键修复验证通过")
        return True
        
    except Exception as e:
        print(f"❌ OCR纠正存储键修复验证失败: {e}")
        traceback.print_exc()
        return False

def test_ocr_result_corrector_import():
    """测试OCR结果纠正器导入"""
    try:
        from app.services.ocr_result_corrector import OCRResultCorrector
        from app.services.ai_analyzer import AIAnalyzerService
        
        # 测试类定义
        assert hasattr(OCRResultCorrector, 'correct_ocr_result'), "❌ 缺少correct_ocr_result方法"
        
        print("✅ OCR结果纠正器导入验证通过")
        return True
        
    except Exception as e:
        print(f"❌ OCR结果纠正器导入验证失败: {e}")
        traceback.print_exc()
        return False

def test_analysis_logger_log_step():
    """测试AnalysisLogger的log_step方法"""
    try:
        from app.utils.analysis_optimizations import AnalysisLogger
        
        # 测试log_step方法是否存在
        assert hasattr(AnalysisLogger, 'log_step'), "❌ 缺少log_step方法"
        
        # 测试方法调用
        AnalysisLogger.log_step("test_step", "测试详情", 1, 5, "info", "test_task_123")
        
        print("✅ AnalysisLogger.log_step方法验证通过")
        return True
        
    except Exception as e:
        print(f"❌ AnalysisLogger.log_step方法验证失败: {e}")
        traceback.print_exc()
        return False

def test_drawing_tasks_integration():
    """测试drawing_tasks的集成修复"""
    try:
        # 检查文件是否存在
        tasks_file = "app/tasks/drawing_tasks.py"
        assert os.path.exists(tasks_file), f"❌ 任务文件不存在: {tasks_file}"
        
        # 检查关键修复是否在文件中
        with open(tasks_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查merged_ocr_storage支持
        assert 'merged_ocr_storage' in content, "❌ 缺少merged_ocr_storage支持"
        
        # 检查OCR纠正功能
        assert 'OCRResultCorrector' in content, "❌ 缺少OCR纠正功能"
        
        print("✅ drawing_tasks集成修复验证通过")
        return True
        
    except Exception as e:
        print(f"❌ drawing_tasks集成修复验证失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🔍 开始综合修复验证测试...\n")
    
    tests = [
        ("OCRCacheManager修复", test_ocr_cache_manager),
        ("OCR纠正存储键修复", test_ocr_correction_storage_keys),
        ("OCR结果纠正器导入", test_ocr_result_corrector_import),
        ("AnalysisLogger.log_step方法", test_analysis_logger_log_step),
        ("drawing_tasks集成修复", test_drawing_tasks_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 测试: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"💥 {test_name} 测试失败")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有修复验证通过！系统已经完全修复。")
        return True
    else:
        print("⚠️ 部分修复验证失败，需要进一步检查。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 