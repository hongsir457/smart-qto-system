#!/usr/bin/env python3
"""
YOLOv8x模型下载脚本
"""

import os
import sys
from pathlib import Path

def download_yolo_model():
    """下载YOLOv8x模型"""
    try:
        print("🚀 开始下载YOLOv8x模型...")
        
        # 导入ultralytics
        from ultralytics import YOLO
        
        # 下载YOLOv8x模型
        print("📥 正在下载YOLOv8x预训练模型...")
        model = YOLO('yolov8x.pt')
        
        print("✅ YOLOv8x模型下载成功！")
        print(f"   模型大小: {os.path.getsize(model.ckpt_path) / (1024*1024):.1f} MB")
        print(f"   模型类别数: {len(model.names)}")
        
        # 创建目标目录
        models_dir = Path("app/services/models")
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存模型到项目目录
        target_path = models_dir / "best.pt"
        model.save(str(target_path))
        
        print(f"💾 模型已保存到: {target_path}")
        print(f"   文件大小: {os.path.getsize(target_path) / (1024*1024):.1f} MB")
        
        # 测试模型加载
        print("\n🧪 测试模型加载...")
        test_model = YOLO(str(target_path))
        print("✅ 模型加载测试成功！")
        print(f"   支持的类别: {len(test_model.names)}个")
        print(f"   包括: {list(test_model.names.values())[:10]}...")
        
        print("\n🎉 YOLOv8x模型部署完成！")
        print("现在您可以运行构件识别功能了：")
        print("   python test_component_detection.py")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请先安装ultralytics: pip install ultralytics")
        return False
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

if __name__ == "__main__":
    success = download_yolo_model()
    sys.exit(0 if success else 1) 