#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试上下文链切片分析器
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.contextual_slice_analyzer import ContextualSliceAnalyzer

def test_contextual_slice_analysis():
    """测试上下文链切片分析"""
    
    print("🚀 开始测试上下文链切片分析器...")
    
    # 初始化分析器
    analyzer = ContextualSliceAnalyzer()
    
    if not analyzer.ai_analyzer or not analyzer.ai_analyzer.is_available():
        print("❌ AI分析器不可用，无法进行测试")
        return False
    
    print("✅ 分析器初始化成功")
    
    # 模拟测试数据
    full_image_path = "test_images/perf_test_large.png"
    slice_images = [
        "test_images/perf_test_large.png",  # 模拟切片1
        "test_images/perf_test_large.png"   # 模拟切片2
    ]
    
    slice_configs = [
        {
            "slice_id": "slice_1",
            "slice_index": 0,
            "slice_position": "top-left",
            "slice_type": "detail",
            "focus_areas": ["components", "dimensions"],
            "slice_bounds": (0, 0, 512, 512)
        },
        {
            "slice_id": "slice_2", 
            "slice_index": 1,
            "slice_position": "bottom-right",
            "slice_type": "detail",
            "focus_areas": ["components", "annotations"],
            "slice_bounds": (512, 512, 512, 512)
        }
    ]
    
    # 检查测试图片是否存在
    if not os.path.exists(full_image_path):
        print(f"❌ 测试图片不存在: {full_image_path}")
        return False
    
    print(f"✅ 找到测试图片: {full_image_path}")
    print(f"📊 切片数量: {len(slice_images)}")
    
    try:
        # 执行上下文链分析
        result = analyzer.analyze_with_contextual_chain(
            full_image_path=full_image_path,
            slice_images=slice_images,
            slice_configs=slice_configs,
            task_id="test_contextual_analysis",
            drawing_id=999
        )
        
        print(f"\n📊 分析结果:")
        print(f"   - 成功: {result.get('success', False)}")
        
        if result.get("success"):
            qto_data = result.get("qto_data", {})
            components = qto_data.get("components", [])
            
            print(f"   - 识别构件数: {len(components)}")
            print(f"   - 分析方法: {result.get('analysis_method', 'N/A')}")
            
            # 显示全局上下文信息
            analysis_metadata = result.get("analysis_metadata", {})
            global_context = analysis_metadata.get("global_context", {})
            
            if global_context:
                print(f"\n🌍 全局上下文:")
                print(f"   - 项目名称: {global_context.get('project_name', 'N/A')}")
                print(f"   - 图纸类型: {global_context.get('drawing_type', 'N/A')}")
                print(f"   - 图纸比例: {global_context.get('scale', 'N/A')}")
                print(f"   - 主要构件类型: {global_context.get('main_component_types', [])}")
            
            # 显示切片分析摘要
            slice_summary = analysis_metadata.get("slice_analysis_summary", {})
            if slice_summary:
                print(f"\n🔗 切片分析摘要:")
                print(f"   - 总切片数: {slice_summary.get('total_slices', 0)}")
                print(f"   - 成功切片数: {slice_summary.get('successful_slices', 0)}")
                print(f"   - 失败切片数: {slice_summary.get('failed_slices', 0)}")
            
            # 显示一致性报告
            consistency_report = analysis_metadata.get("consistency_report", {})
            if consistency_report:
                print(f"\n✅ 一致性验证:")
                print(f"   - 项目信息一致: {consistency_report.get('project_info_consistent', False)}")
                print(f"   - 构件编号一致: {consistency_report.get('component_numbering_consistent', False)}")
                print(f"   - 比例一致: {consistency_report.get('scale_consistent', False)}")
                
                warnings = consistency_report.get("warnings", [])
                if warnings:
                    print(f"   ⚠️ 警告: {len(warnings)} 项")
                    for warning in warnings[:3]:  # 只显示前3个警告
                        print(f"      - {warning}")
            
            return True
        else:
            print(f"   ❌ 分析失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        return False

if __name__ == "__main__":
    print("🧪 上下文链切片分析器测试")
    print("="*60)
    
    success = test_contextual_slice_analysis()
    
    if success:
        print("\n✅ 测试成功！上下文链切片分析器工作正常")
        print("\n💡 使用建议:")
        print("   1. 对于大图纸，使用此分析器可以获得更好的上下文连贯性")
        print("   2. 切片分析将保持与全图分析的一致性")
        print("   3. 前序切片的结果会传递给后续切片，避免重复识别")
    else:
        print("\n❌ 测试失败，请检查配置和错误信息")
    
    print("="*60) 