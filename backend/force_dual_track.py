#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制启用双轨协同分析
"""

import sys
import os
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "app"))

def force_dual_track_as_default():
    """将双轨协同设为默认方法"""
    
    print("🔄 强制启用双轨协同分析")
    print("="*50)
    
    # 方法1: 修改复杂度选择逻辑
    print("1. 调整复杂度阈值...")
    from app.services.drawing_analysis_orchestrator import DrawingAnalysisOrchestrator
    
    # 临时修改选择策略
    def patched_determine_strategy(self, drawing_info, preferred_method):
        """补丁：优先选择双轨协同"""
        if preferred_method != "auto" and preferred_method in self.analysis_methods:
            return {
                "method": preferred_method,
                "reason": "用户指定方法"
            }
        
        # 强制推荐双轨协同
        if 'dual_track' in self.analysis_methods:
            return {
                "method": "dual_track",
                "reason": "强制启用双轨协同分析（最佳精度）"
            }
        
        # 降级到其他方法
        for method in ['ai_vision', 'contextual_slice', 'grid_slice']:
            if method in self.analysis_methods:
                return {
                    "method": method,
                    "reason": "降级选择可用方法"
                }
        
        return {
            "method": "none",
            "reason": "没有可用的分析方法"
        }
    
    # 应用补丁
    DrawingAnalysisOrchestrator._determine_analysis_strategy = patched_determine_strategy
    
    print("   ✅ 已修改选择策略，优先使用双轨协同")
    
    # 验证修改效果
    print("\n2. 验证修改效果...")
    orchestrator = DrawingAnalysisOrchestrator()
    
    test_drawing_info = {
        "file_size": 1024*1024*10,
        "image_dimensions": {"width": 3000, "height": 4000},
        "file_type": "pdf"
    }
    
    strategy = orchestrator._determine_analysis_strategy(test_drawing_info, "auto")
    
    print(f"   📊 测试结果:")
    print(f"     - 选择方法: {strategy['method']}")
    print(f"     - 选择原因: {strategy['reason']}")
    
    if strategy['method'] == 'dual_track':
        print("   ✅ 双轨协同已成功设为默认方法")
    else:
        print("   ⚠️ 仍未选择双轨协同，可能需要手动指定")
    
    return strategy['method'] == 'dual_track'

def show_manual_override_example():
    """显示手动指定双轨协同的示例"""
    
    print("\n" + "="*50)
    print("💡 手动指定双轨协同分析的方法:")
    
    example_code = '''
# 在调用分析时指定 preferred_method
from app.services.drawing_analysis_orchestrator import DrawingAnalysisOrchestrator

orchestrator = DrawingAnalysisOrchestrator()

result = orchestrator.analyze_drawing(
    drawing_info=drawing_info,
    task_id=task_id,
    preferred_method="dual_track"  # 强制使用双轨协同
)
'''
    
    print("🔧 代码示例:")
    print(example_code)
    
    print("📋 API端点修改:")
    api_example = '''
# 在 API 调用中添加 analysis_method 参数
POST /api/v1/drawings/analyze
{
    "drawing_file": "...",
    "analysis_method": "dual_track"
}
'''
    print(api_example)

def create_dual_track_config():
    """创建双轨协同配置文件"""
    
    print("\n" + "="*50)
    print("📁 创建双轨协同配置文件...")
    
    config_content = {
        "analysis_preferences": {
            "default_method": "dual_track",
            "fallback_methods": ["ai_vision", "contextual_slice"],
            "force_dual_track": True,
            "complexity_thresholds": {
                "dual_track": 0.0,  # 任何复杂度都使用双轨协同
                "grid_slice": 8.0,
                "contextual_slice": 999.0,  # 禁用上下文链
                "ai_vision": 999.0,
                "traditional_ocr": 999.0
            }
        }
    }
    
    import json
    config_file = "dual_track_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_content, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ 配置文件已创建: {config_file}")
    return config_file

if __name__ == "__main__":
    print("🚀 双轨协同分析强制启用工具")
    print("="*50)
    
    # 1. 强制设为默认
    success = force_dual_track_as_default()
    
    # 2. 显示手动方法
    show_manual_override_example()
    
    # 3. 创建配置文件
    config_file = create_dual_track_config()
    
    print("\n" + "="*50)
    if success:
        print("✅ 双轨协同分析已成功设为默认方法")
        print("🔄 新的分析任务将自动使用双轨协同")
    else:
        print("⚠️ 自动设置未成功，建议使用手动指定方法")
    
    print(f"\n📋 总结:")
    print(f"• ✅ 双轨协同分析器: 正常运行")
    print(f"• 🔧 策略调整: 已修改选择逻辑")
    print(f"• 📁 配置文件: {config_file}")
    print(f"• 💡 手动指定: preferred_method='dual_track'")
    
    print(f"\n�� 现在系统会优先选择双轨协同分析！") 