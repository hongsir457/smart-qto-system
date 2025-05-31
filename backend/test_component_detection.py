#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构件识别功能测试脚本
测试YOLO模型的构件检测能力
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.services.component_detection import ComponentDetector

def test_component_detection():
    """测试构件识别功能"""
    print("🔍 构件识别功能测试")
    print("=" * 60)
    
    # 1. 初始化构件检测器
    print("\n📋 初始化构件检测器...")
    try:
        detector = ComponentDetector()
        if detector.model is None:
            print("⚠️  YOLO模型未能加载 - 这是正常的，因为模型文件可能不存在")
            print("   模型路径应该在: app/services/models/best.pt")
            print("   您需要训练或下载一个YOLO模型文件")
        else:
            print("✅ YOLO模型加载成功")
            print(f"   模型类别: {list(detector.model.names.values())}")
            print(f"   类别数量: {len(detector.model.names)}")
    except Exception as e:
        print(f"❌ 构件检测器初始化失败: {str(e)}")
        return
    
    # 2. 测试图片文件
    test_images = [
        "complex_building_plan.png",
        "../uploads/一层柱结构改造加固平面图.pdf"  # 如果存在的话
    ]
    
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n🧪 测试图片: {image_path}")
            print("-" * 40)
            
            try:
                results = detector.detect_components(image_path)
                
                print("📊 检测结果:")
                total_components = 0
                
                for component_type, components in results.items():
                    count = len(components)
                    total_components += count
                    print(f"   - {component_type}: {count}个")
                    
                    # 显示前3个构件的详细信息
                    if count > 0:
                        for i, component in enumerate(components[:3]):
                            conf = component.get('confidence', 0)
                            dims = component.get('dimensions', {})
                            width = dims.get('width', 0)
                            height = dims.get('height', 0)
                            print(f"     [{i+1}] 置信度: {conf:.2f}, 尺寸: {width:.0f}x{height:.0f}mm")
                        
                        if count > 3:
                            print(f"     ... 还有 {count - 3} 个")
                
                if total_components == 0:
                    print("   ⚠️  未检测到任何构件")
                    if detector.model is None:
                        print("   原因: YOLO模型未加载")
                    else:
                        print("   原因: 图片中可能没有可识别的建筑构件，或模型需要针对建筑图纸训练")
                else:
                    print(f"   ✅ 总共检测到 {total_components} 个构件")
                    
            except Exception as e:
                print(f"   ❌ 检测失败: {str(e)}")
        else:
            print(f"\n⏭️  跳过 {image_path} (文件不存在)")
    
    # 3. 构件识别配置说明
    print("\n💡 构件识别配置说明:")
    print("-" * 30)
    print("1. YOLO模型文件位置: backend/app/services/models/best.pt")
    print("2. 如果模型不存在，构件识别将返回空结果")
    print("3. 推荐使用专门训练的建筑构件检测模型")
    print("4. 当前使用COCO预训练模型的类别映射（如果有模型）")
    
    print("\n🎯 使用建议:")
    print("- 上传清晰的建筑平面图")
    print("- 确保图纸包含明显的构件轮廓")
    print("- 对于最佳效果，建议使用专门的建筑YOLO模型")

if __name__ == "__main__":
    try:
        test_component_detection()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc() 