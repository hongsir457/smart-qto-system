#!/usr/bin/env python3
"""
语法修复验证脚本
测试所有关键模块是否可以正常导入
"""

import sys
import traceback

def test_module_import(module_name):
    """测试模块导入"""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - 导入成功")
        return True
    except Exception as e:
        print(f"❌ {module_name} - 导入失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🔧 开始语法修复验证测试...")
    print("=" * 50)
    
    # 测试关键模块
    modules_to_test = [
        "app.services.ocr.paddle_ocr",
        "app.services.enhanced_grid_slice_analyzer", 
        "app.tasks.drawing_tasks",
        "app.core.celery_app",
        "app.utils.analysis_optimizations",
        "app.services.ocr_result_corrector"
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module in modules_to_test:
        if test_module_import(module):
            success_count += 1
    
    print("=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 个模块导入成功")
    
    if success_count == total_count:
        print("🎉 所有语法错误已修复！系统可以正常启动。")
        return 0
    else:
        print("⚠️ 仍有模块存在语法错误，需要进一步修复。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 