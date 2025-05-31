#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的构件检测测试脚本
测试YOLOv8x模型和传统图像处理方法的构件识别能力
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.component_detection import ComponentDetector

def test_component_detection():
    """测试构件检测功能"""
    print("🚀 开始测试优化后的构件检测功能...")
    print("=" * 60)
    
    # 初始化检测器
    detector = ComponentDetector()
    
    # 测试图像路径
    test_images = [
        "test_images/complex_building_plan.png",
        "test_images/一层柱结构改造加固平面图.pdf",
        "test_images/sample_floorplan.jpg"  # 如果有其他测试图像
    ]
    
    for image_path in test_images:
        if not os.path.exists(image_path):
            print(f"⚠️  测试图像不存在: {image_path}")
            continue
            
        print(f"\n📸 测试图像: {image_path}")
        print("-" * 40)
        
        try:
            # 执行构件检测
            results = detector.detect_components(image_path)
            
            # 统计检测结果
            total_components = 0
            for component_type, components in results.items():
                count = len(components)
                total_components += count
                if count > 0:
                    print(f"  {component_type}: {count}个")
                    
                    # 显示前3个检测结果的详细信息
                    for i, comp in enumerate(components[:3]):
                        confidence = comp.get('confidence', 0)
                        class_name = comp.get('class_name', 'unknown')
                        dimensions = comp.get('dimensions', {})
                        width = dimensions.get('width', 0)
                        height = dimensions.get('height', 0)
                        
                        print(f"    [{i+1}] 置信度: {confidence:.2f}, "
                              f"类别: {class_name}, "
                              f"尺寸: {width:.0f}×{height:.0f}mm")
            
            print(f"\n✅ 总计检测到 {total_components} 个构件")
            
            # 保存检测结果到JSON文件
            output_file = f"detection_results_{Path(image_path).stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"📄 检测结果已保存到: {output_file}")
            
        except Exception as e:
            print(f"❌ 检测失败: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 测试完成！")

def test_model_info():
    """测试模型信息"""
    print("\n🔍 检查模型信息...")
    print("-" * 40)
    
    detector = ComponentDetector()
    
    if detector.model is not None:
        print(f"✅ YOLO模型已加载")
        print(f"📊 支持的类别数量: {len(detector.model.names)}")
        print(f"🏷️  类别名称示例: {list(detector.model.names.values())[:10]}")
        
        # 测试智能映射
        print("\n🧠 智能类别映射测试:")
        test_classes = ['book', 'bottle', 'chair', 'dining table', 'laptop']
        for class_name in test_classes:
            # 模拟检测结果
            class_id = None
            for id, name in detector.model.names.items():
                if name.lower() == class_name:
                    class_id = id
                    break
            
            if class_id is not None:
                # 模拟边界框
                component_type = detector._get_component_type(class_id, 100, 100, 300, 200)
                print(f"  {class_name} → {component_type}")
    else:
        print("⚠️  YOLO模型未加载，将使用演示数据模式")

def create_sample_test_image():
    """创建一个简单的测试图像（如果没有测试图像）"""
    try:
        import cv2
        import numpy as np
        
        # 创建一个简单的建筑平面图模拟图像
        img = np.ones((600, 800, 3), dtype=np.uint8) * 255  # 白色背景
        
        # 绘制一些矩形模拟建筑构件
        # 墙体（长矩形）
        cv2.rectangle(img, (50, 50), (750, 80), (0, 0, 0), 2)
        cv2.rectangle(img, (50, 520), (750, 550), (0, 0, 0), 2)
        cv2.rectangle(img, (50, 50), (80, 550), (0, 0, 0), 2)
        cv2.rectangle(img, (720, 50), (750, 550), (0, 0, 0), 2)
        
        # 柱子（小正方形）
        cv2.rectangle(img, (200, 200), (230, 230), (0, 0, 0), -1)
        cv2.rectangle(img, (400, 200), (430, 230), (0, 0, 0), -1)
        cv2.rectangle(img, (600, 200), (630, 230), (0, 0, 0), -1)
        
        # 梁（长条形）
        cv2.rectangle(img, (150, 300), (650, 320), (128, 128, 128), -1)
        
        # 保存测试图像
        os.makedirs("test_images", exist_ok=True)
        cv2.imwrite("test_images/sample_floorplan.jpg", img)
        print("✅ 已创建示例测试图像: test_images/sample_floorplan.jpg")
        
    except ImportError:
        print("⚠️  OpenCV未安装，无法创建示例图像")

if __name__ == "__main__":
    print("🏗️  智能建筑构件检测系统 - 优化版测试")
    print("=" * 60)
    
    # 检查测试图像目录
    if not os.path.exists("test_images"):
        os.makedirs("test_images")
        print("📁 已创建test_images目录")
    
    # 如果没有测试图像，创建一个示例
    if not any(os.path.exists(f"test_images/{img}") for img in 
               ["complex_building_plan.png", "sample_floorplan.jpg"]):
        create_sample_test_image()
    
    # 测试模型信息
    test_model_info()
    
    # 测试构件检测
    test_component_detection()
    
    print("\n🎉 所有测试完成！")
    print("\n💡 提示:")
    print("   - 如果检测结果不理想，可以尝试使用更清晰的建筑图纸")
    print("   - 建议收集专门的建筑构件数据集进行模型微调")
    print("   - 可以调整置信度阈值和几何特征参数来优化检测效果") 