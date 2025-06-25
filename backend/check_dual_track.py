#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查双轨协同分析器状态
"""

import sys
import os
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "app"))

def check_dual_track_status():
    """检查双轨协同分析器状态"""
    
    print("🔍 检查双轨协同分析器状态")
    print("="*50)
    
    try:
        # 1. 检查编排器初始化
        print("1. 检查编排器初始化...")
        from app.services.drawing_analysis_orchestrator import DrawingAnalysisOrchestrator
        orchestrator = DrawingAnalysisOrchestrator()
        
        # 2. 检查可用方法
        available_methods = orchestrator.get_available_methods()
        print(f"   ✅ 可用分析方法: {available_methods}")
        
        # 3. 检查双轨协同是否可用
        dual_track_available = 'dual_track' in orchestrator.analysis_methods
        print(f"   🔄 双轨协同是否可用: {dual_track_available}")
        
        if dual_track_available:
            print("   ✅ 双轨协同分析器已正确初始化")
        else:
            print("   ❌ 双轨协同分析器未初始化")
            print("   🔍 初始化的分析器:", list(orchestrator.analysis_methods.keys()))
        
        # 4. 检查方法信息
        method_info = orchestrator.get_method_info()
        print(f"\n2. 方法信息:")
        for method, info in method_info.items():
            print(f"   📋 {method}: {info['name']}")
        
        # 5. 模拟复杂度评分测试
        print(f"\n3. 复杂度选择测试:")
        test_cases = [
            {"file_size": 1024*1024*5, "width": 2048, "height": 2048, "file_type": "png", "desc": "中等图纸"},
            {"file_size": 1024*1024*20, "width": 4096, "height": 4096, "file_type": "pdf", "desc": "高质量图纸"},
            {"file_size": 1024*1024*50, "width": 8192, "height": 8192, "file_type": "dwg", "desc": "超大CAD图纸"},
            {"file_size": 1024*1024*10, "width": 3000, "height": 4000, "file_type": "pdf", "desc": "当前测试场景"}
        ]
        
        for i, case in enumerate(test_cases, 1):
            try:
                score = orchestrator._calculate_complexity_score(
                    case["file_size"], case["width"], case["height"], case["file_type"]
                )
                
                strategy = orchestrator._determine_analysis_strategy(case, "auto")
                
                print(f"   案例{i} ({case['desc']}):")
                print(f"     - 尺寸: {case['width']}x{case['height']}")
                print(f"     - 大小: {case['file_size']//1024//1024}MB")
                print(f"     - 类型: {case['file_type']}")
                print(f"     - 复杂度: {score:.1f}")
                print(f"     - 选择方法: {strategy['method']}")
                print(f"     - 选择原因: {strategy['reason']}")
                print()
            except Exception as e:
                print(f"   案例{i} 测试失败: {e}")
                print()
        
        return dual_track_available
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def suggest_solutions():
    """建议解决方案"""
    
    print("\n" + "="*50)
    print("💡 解决方案建议:")
    
    solutions = [
        "1. 降低双轨协同触发阈值（从7.0降到5.0）",
        "2. 检查双轨协同分析器是否正确导入",
        "3. 手动指定preferred_method='dual_track'",
        "4. 调整当前图纸的复杂度评分权重"
    ]
    
    for solution in solutions:
        print(f"   💭 {solution}")

if __name__ == "__main__":
    print("🔄 双轨协同分析器状态检查")
    print("="*50)
    
    # 检查状态
    is_available = check_dual_track_status()
    
    # 建议解决方案
    suggest_solutions()
    
    print("\n" + "="*50)
    if is_available:
        print("✅ 双轨协同分析器运行正常")
    else:
        print("⚠️ 双轨协同分析器需要修复") 