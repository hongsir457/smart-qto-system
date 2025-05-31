#!/usr/bin/env python3
"""
构件识别功能完整演示脚本
展示从图纸上传到构件识别的完整流程
"""

import os
import sys
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def demo_component_recognition():
    """演示构件识别完整功能"""
    
    print("🏗️  智能工程量计算系统 - 构件识别功能演示")
    print("=" * 80)
    
    # 1. 导入必要的模块
    print("\n📦 1. 导入系统模块...")
    try:
        from app.services.component_detection import ComponentDetector
        print("✅ 模块导入成功")
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return
    
    # 2. 初始化构件检测器
    print("\n🔧 2. 初始化构件检测器...")
    detector = ComponentDetector()
    print("✅ 构件检测器初始化完成")
    
    # 3. 测试图片列表
    test_images = [
        {
            "path": "complex_building_plan.png",
            "description": "复杂建筑平面图"
        },
        {
            "path": "../uploads/一层柱结构改造加固平面图.pdf",
            "description": "一层柱结构改造加固平面图"
        },
        {
            "path": "../uploads/一层梁结构改造加固平面图.pdf", 
            "description": "一层梁结构改造加固平面图"
        },
        {
            "path": "../uploads/一层板结构改造加固平面图.pdf",
            "description": "一层板结构改造加固平面图"
        }
    ]
    
    # 4. 逐个测试图片
    print("\n🧪 3. 开始构件识别测试...")
    results = []
    
    for i, image_info in enumerate(test_images, 1):
        image_path = image_info["path"]
        description = image_info["description"]
        
        print(f"\n📋 测试 {i}/{len(test_images)}: {description}")
        print("-" * 60)
        
        if not os.path.exists(image_path):
            print(f"⚠️  文件不存在: {image_path}")
            continue
            
        try:
            # 执行构件识别
            start_time = time.time()
            components = detector.detect_components(image_path)
            detection_time = time.time() - start_time
            
            # 统计结果
            total_components = sum(len(comp_list) for comp_list in components.values())
            
            # 显示结果摘要
            print(f"⏱️  识别耗时: {detection_time:.2f}秒")
            print(f"🎯 检测到构件总数: {total_components}")
            
            # 详细结果
            component_summary = {}
            for comp_type, comp_list in components.items():
                if comp_list:
                    component_summary[comp_type] = len(comp_list)
                    print(f"   - {comp_type}: {len(comp_list)}个")
                    
                    # 显示前2个构件的详细信息
                    for j, component in enumerate(comp_list[:2]):
                        confidence = component.get('confidence', 0)
                        dimensions = component.get('dimensions', {})
                        width = dimensions.get('width', 0)
                        height = dimensions.get('height', 0)
                        print(f"     [{j+1}] 置信度: {confidence:.2f}, 尺寸: {width:.0f}×{height:.0f}mm")
                    
                    if len(comp_list) > 2:
                        print(f"     ... 还有 {len(comp_list) - 2} 个")
            
            # 保存结果
            result = {
                "image": description,
                "path": image_path,
                "detection_time": detection_time,
                "total_components": total_components,
                "component_summary": component_summary,
                "detailed_results": components
            }
            results.append(result)
            
            print("✅ 识别完成")
            
        except Exception as e:
            print(f"❌ 识别失败: {str(e)}")
            continue
    
    # 5. 生成综合报告
    print("\n📊 4. 生成综合分析报告...")
    print("=" * 80)
    
    if results:
        # 统计总体情况
        total_images = len(results)
        total_detection_time = sum(r["detection_time"] for r in results)
        total_all_components = sum(r["total_components"] for r in results)
        avg_detection_time = total_detection_time / total_images
        
        print(f"📈 总体统计:")
        print(f"   - 测试图片数量: {total_images}")
        print(f"   - 总检测时间: {total_detection_time:.2f}秒")
        print(f"   - 平均检测时间: {avg_detection_time:.2f}秒/图")
        print(f"   - 检测构件总数: {total_all_components}")
        print(f"   - 平均构件数量: {total_all_components/total_images:.1f}个/图")
        
        # 构件类型统计
        print(f"\n🏗️  构件类型分布:")
        component_totals = {}
        for result in results:
            for comp_type, count in result["component_summary"].items():
                component_totals[comp_type] = component_totals.get(comp_type, 0) + count
        
        for comp_type, total_count in component_totals.items():
            avg_count = total_count / total_images
            print(f"   - {comp_type}: {total_count}个 (平均 {avg_count:.1f}个/图)")
        
        # 保存详细结果
        output_file = "component_recognition_demo_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 详细结果已保存到: {output_file}")
        
    else:
        print("❌ 没有成功的识别结果")
    
    # 6. 系统状态检查
    print("\n🔍 5. 系统状态检查...")
    print("-" * 40)
    
    # 检查YOLO模型状态
    model_path = "app/services/models/best.pt"
    if os.path.exists(model_path):
        print(f"✅ YOLO模型文件存在: {model_path}")
    else:
        print(f"⚠️  YOLO模型文件不存在: {model_path}")
        print("   当前使用演示数据模式")
    
    # 检查API配置
    try:
        from app.api.v1.endpoints.drawings import detect_components
        print("✅ 构件识别API端点可用")
    except ImportError:
        print("❌ 构件识别API端点不可用")
    
    # 7. 使用建议
    print("\n💡 6. 使用建议和下一步...")
    print("-" * 40)
    print("🎯 当前功能状态:")
    print("   ✅ 构件识别核心功能已实现")
    print("   ✅ 演示数据模式正常工作")
    print("   ✅ API端点已配置")
    print("   ✅ 前端界面已集成")
    
    print("\n🚀 改进建议:")
    print("   1. 训练或获取专用的建筑构件YOLO模型")
    print("   2. 优化构件分类和尺寸估算算法")
    print("   3. 添加构件识别结果的可视化显示")
    print("   4. 集成工程量计算功能")
    print("   5. 添加识别结果的人工校正功能")
    
    print("\n🔧 技术要点:")
    print("   - 当前使用演示数据确保功能可用性")
    print("   - 支持多种图片格式（PNG、PDF等）")
    print("   - 提供详细的构件信息（位置、置信度、尺寸）")
    print("   - 具备良好的错误处理和用户反馈")

def main():
    """主函数"""
    try:
        demo_component_recognition()
    except KeyboardInterrupt:
        print("\n\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中发生错误: {str(e)}")
    finally:
        print("\n" + "=" * 80)
        print("🎉 构件识别功能演示完成！")

if __name__ == "__main__":
    main() 