#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试导入路径 - 查找extract_text函数的真实来源
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

def debug_extract_text_import():
    """调试extract_text函数的导入路径"""
    print("🔍 调试extract_text函数导入路径")
    print("=" * 60)
    
    try:
        # 尝试导入并检查来源
        print("🔄 尝试导入 app.services.drawing...")
        from app.services import drawing
        print(f"   ✅ 导入成功: {drawing}")
        print(f"   📁 模块文件: {drawing.__file__ if hasattr(drawing, '__file__') else '无文件信息'}")
        
        # 检查extract_text函数
        if hasattr(drawing, 'extract_text'):
            extract_text = drawing.extract_text
            print(f"   ✅ 找到extract_text函数: {extract_text}")
            print(f"   📍 函数定义位置: {extract_text.__module__}")
            print(f"   📋 函数代码位置: {extract_text.__code__.co_filename}:{extract_text.__code__.co_firstlineno}")
            
            # 测试调用
            test_result = extract_text("test.png")
            print(f"   🧪 测试调用结果: {test_result[:100]}...")
            
        else:
            print("   ❌ 未找到extract_text函数")
            print(f"   📋 可用属性: {dir(drawing)}")
        
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
    
    # 尝试另一种导入方式
    try:
        print("\n🔄 尝试直接导入 extract_text...")
        from app.services.drawing import extract_text
        print(f"   ✅ 导入成功: {extract_text}")
        print(f"   📍 函数定义位置: {extract_text.__module__}")
        print(f"   📋 函数代码位置: {extract_text.__code__.co_filename}:{extract_text.__code__.co_firstlineno}")
        
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
    
    # 检查是否有其他extract_text
    try:
        print("\n🔄 搜索系统中的所有extract_text函数...")
        
        # 检查drawing_main
        from app.services.drawing_main import extract_text as main_extract_text
        print(f"   📍 drawing_main.extract_text: {main_extract_text.__code__.co_filename}:{main_extract_text.__code__.co_firstlineno}")
        
        # 检查drawing_original_backup
        from app.services.drawing_original_backup import extract_text as backup_extract_text
        print(f"   📍 drawing_original_backup.extract_text: {backup_extract_text.__code__.co_filename}:{backup_extract_text.__code__.co_firstlineno}")
        
    except ImportError as e:
        print(f"   ❌ 检查其他模块失败: {e}")

if __name__ == "__main__":
    debug_extract_text_import() 