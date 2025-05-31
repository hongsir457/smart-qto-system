#!/usr/bin/env python3
"""
构件识别API测试脚本
测试 /api/v1/drawings/{drawing_id}/detect-components 端点
"""

import requests
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_component_detection_api():
    """测试构件识别API"""
    
    print("🔍 构件识别API测试")
    print("=" * 60)
    
    # API基础URL
    base_url = "http://localhost:8000"
    
    # 测试用的图纸ID（假设存在）
    test_drawing_id = 1
    
    # 构建API端点URL
    api_url = f"{base_url}/api/v1/drawings/{test_drawing_id}/detect-components"
    
    print(f"📡 测试API端点: {api_url}")
    
    try:
        # 发送POST请求
        print("📤 发送构件识别请求...")
        response = requests.post(api_url, timeout=30)
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 解析响应数据
            result = response.json()
            
            print("✅ API调用成功!")
            print("\n📋 检测结果:")
            print("-" * 40)
            
            # 显示检测到的构件统计
            total_components = 0
            for component_type, components in result.items():
                count = len(components)
                total_components += count
                print(f"   - {component_type}: {count}个")
                
                # 显示前3个构件的详细信息
                for i, component in enumerate(components[:3]):
                    confidence = component.get('confidence', 0)
                    dimensions = component.get('dimensions', {})
                    width = dimensions.get('width', 0)
                    height = dimensions.get('height', 0)
                    print(f"     [{i+1}] 置信度: {confidence:.2f}, 尺寸: {width:.0f}x{height:.0f}mm")
                
                if len(components) > 3:
                    print(f"     ... 还有 {len(components) - 3} 个")
            
            print(f"\n🎯 总共检测到 {total_components} 个构件")
            
            # 保存结果到文件
            output_file = "component_detection_result.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"💾 结果已保存到: {output_file}")
            
        elif response.status_code == 404:
            print("❌ 图纸不存在 (404)")
            print("💡 请确保图纸ID存在于数据库中")
            
        elif response.status_code == 500:
            print("❌ 服务器内部错误 (500)")
            try:
                error_detail = response.json()
                print(f"错误详情: {error_detail}")
            except:
                print(f"错误详情: {response.text}")
                
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败 - 请确保后端服务正在运行")
        print("💡 启动命令: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时 - 构件识别可能需要较长时间")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

def test_direct_component_detection():
    """直接测试构件检测功能（不通过API）"""
    
    print("\n🔧 直接构件检测测试")
    print("=" * 60)
    
    try:
        from app.services.component_detection import ComponentDetector
        
        # 初始化检测器
        detector = ComponentDetector()
        
        # 测试图片路径
        test_images = [
            "complex_building_plan.png",
            "../uploads/一层柱结构改造加固平面图.pdf"
        ]
        
        for image_path in test_images:
            if os.path.exists(image_path):
                print(f"\n🧪 测试图片: {image_path}")
                print("-" * 40)
                
                # 执行构件检测
                result = detector.detect_components(image_path)
                
                # 显示结果
                total_components = sum(len(components) for components in result.values())
                print(f"✅ 检测完成，共发现 {total_components} 个构件")
                
                for component_type, components in result.items():
                    if components:
                        print(f"   - {component_type}: {len(components)}个")
            else:
                print(f"⚠️  图片不存在: {image_path}")
                
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🏗️  智能工程量计算系统 - 构件识别测试")
    print("=" * 80)
    
    # 测试直接构件检测
    test_direct_component_detection()
    
    # 测试API端点
    test_component_detection_api()
    
    print("\n" + "=" * 80)
    print("📝 测试说明:")
    print("1. 直接测试验证构件检测核心功能")
    print("2. API测试验证前端调用接口")
    print("3. 如果API测试失败，请确保后端服务正在运行")
    print("4. 当前使用演示数据模式（YOLO模型未加载）")

if __name__ == "__main__":
    main() 