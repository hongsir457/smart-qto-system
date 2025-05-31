#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO模型测试脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

def test_yolo_model():
    """测试YOLO模型加载和基本功能"""
    print("=" * 60)
    print("YOLO模型测试")
    print("=" * 60)
    
    try:
        # 检查模型文件是否存在
        model_path = Path("app/models/best.pt")
        print(f"检查模型文件: {model_path.absolute()}")
        
        if model_path.exists():
            print(f"✅ 模型文件存在，大小: {model_path.stat().st_size / (1024*1024):.1f} MB")
        else:
            print(f"❌ 模型文件不存在")
            return False
        
        # 测试ultralytics库
        try:
            from ultralytics import YOLO
            print("✅ ultralytics库导入成功")
        except ImportError as e:
            print(f"❌ ultralytics库导入失败: {e}")
            return False
        
        # 加载模型
        print("\n加载YOLO模型...")
        try:
            model = YOLO(str(model_path))
            print("✅ YOLO模型加载成功!")
            
            # 显示模型信息
            print(f"   模型类型: {type(model)}")
            if hasattr(model, 'names'):
                print(f"   类别数量: {len(model.names)}")
                print(f"   类别列表: {list(model.names.values())[:10]}...")  # 显示前10个类别
            
            return True
            
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def test_config_path():
    """测试配置路径"""
    print("\n" + "=" * 60)
    print("配置路径测试")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        print(f"配置的MODEL_PATH: {settings.MODEL_PATH}")
        print(f"MODEL_PATH是否存在: {settings.MODEL_PATH.exists()}")
        
        # 检查模型文件
        model_file = settings.MODEL_PATH / "best.pt"
        print(f"模型文件路径: {model_file}")
        print(f"模型文件是否存在: {model_file.exists()}")
        
        if model_file.exists():
            print(f"模型文件大小: {model_file.stat().st_size / (1024*1024):.1f} MB")
            return True
        else:
            print("❌ 模型文件在配置路径中不存在")
            return False
            
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_drawing_service():
    """测试drawing服务中的模型加载"""
    print("\n" + "=" * 60)
    print("Drawing服务测试")
    print("=" * 60)
    
    try:
        # 重新导入以确保使用最新配置
        import importlib
        import app.services.drawing
        importlib.reload(app.services.drawing)
        
        from app.services.drawing import load_yolo_model
        
        print("调用load_yolo_model函数...")
        model = load_yolo_model()
        
        if model:
            print("✅ Drawing服务中的YOLO模型加载成功!")
            return True
        else:
            print("❌ Drawing服务中的YOLO模型加载失败")
            return False
            
    except Exception as e:
        print(f"❌ Drawing服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("开始YOLO模型测试...")
    
    results = []
    
    # 运行测试
    results.append(("模型文件测试", test_yolo_model()))
    results.append(("配置路径测试", test_config_path()))
    results.append(("Drawing服务测试", test_drawing_service()))
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！YOLO模型已成功加载！")
    else:
        print("⚠️  部分测试失败，请检查相关配置")
    print("=" * 60)

if __name__ == "__main__":
    main() 