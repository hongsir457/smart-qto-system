#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实图片OCR测试脚本
用于测试用户上传的建筑图纸OCR识别效果
"""

import os
import sys
import time
import cv2
import numpy as np
import pytesseract
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Tesseract路径
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "tesseract"
]

for path in tesseract_paths:
    if os.path.exists(path) or path == "tesseract":
        pytesseract.pytesseract.tesseract_cmd = path
        print(f"✓ 设置Tesseract路径: {path}")
        break

def test_image_ocr(image_path):
    """测试单个图片的OCR识别效果"""
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"测试图片: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    try:
        # 导入优化后的OCR函数
        from app.services.drawing import extract_text
        
        # 测试优化后的OCR
        print("[测试] 使用优化后的OCR方法...")
        start_time = time.time()
        
        result = extract_text(image_path)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if "error" in result:
            print(f"❌ OCR识别失败: {result['error']}")
            return
        
        if "warning" in result:
            print(f"⚠️ OCR警告: {result['warning']}")
            return
        
        extracted_text = result.get("text", "")
        
        print(f"\n优化OCR结果:")
        print(f"{'='*40}")
        print(f"识别文字长度: {len(extracted_text)} 字符")
        print(f"处理时间: {processing_time:.2f} 秒")
        
        if extracted_text:
            print(f"\n识别内容预览:")
            print("-" * 40)
            # 显示前500字符
            preview = extracted_text[:500]
            if len(extracted_text) > 500:
                preview += "\n... (内容过长，已截断)"
            print(preview)
            
            # 分析识别到的关键信息
            analyze_extracted_content(extracted_text)
        else:
            print("❌ 未识别到任何文字")
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_extracted_content(text):
    """分析提取的文字内容"""
    import re
    
    print(f"\n内容分析:")
    print("-" * 40)
    
    # 统计数字
    numbers = re.findall(r'\b\d+\b', text)
    print(f"识别到的数字: {len(numbers)} 个")
    if numbers:
        # 显示一些数字示例
        sample_numbers = sorted(set(numbers), key=int)[:10]
        print(f"数字示例: {', '.join(sample_numbers)}")
    
    # 统计尺寸格式
    dimensions = re.findall(r'\b\d+x\d+(?:x\d+)?\b', text.lower())
    print(f"识别到的尺寸格式: {len(dimensions)} 个")
    if dimensions:
        unique_dimensions = list(set(dimensions))[:5]
        print(f"尺寸示例: {', '.join(unique_dimensions)}")
    
    # 检查建筑关键词
    building_keywords = [
        'foundation', 'plan', 'scale', 'wall', 'column', 'beam', 
        'kitchen', 'bedroom', 'bathroom', 'garage', 'storage',
        'concrete', 'steel', 'grade', 'dimension', 'depth',
        'living', 'room', 'type', 'mm', 'notes', 'section',
        'elevation', 'detail', 'reinforcement', 'floor'
    ]
    
    text_lower = text.lower()
    found_keywords = [kw for kw in building_keywords if kw in text_lower]
    
    print(f"识别到的建筑关键词: {len(found_keywords)} 个")
    if found_keywords:
        print(f"关键词: {', '.join(found_keywords[:10])}")
    
    # 检查中文内容
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    if chinese_chars:
        print(f"识别到的中文字符: {len(chinese_chars)} 个")

def test_multiple_images():
    """测试多个图片"""
    # 常见的图片格式
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf']
    
    # 查找当前目录下的图片文件
    current_dir = Path('.')
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(current_dir.glob(f'*{ext}'))
        image_files.extend(current_dir.glob(f'*{ext.upper()}'))
    
    if not image_files:
        print("❌ 当前目录下没有找到图片文件")
        print("支持的格式: " + ", ".join(image_extensions))
        return
    
    print(f"找到 {len(image_files)} 个图片文件:")
    for i, img_file in enumerate(image_files, 1):
        print(f"{i}. {img_file.name}")
    
    print(f"\n开始测试...")
    
    for img_file in image_files:
        test_image_ocr(str(img_file))

def main():
    """主函数"""
    print("建筑图纸OCR识别测试工具")
    print("=" * 60)
    
    # 检查Tesseract版本
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract版本: {version}")
    except Exception as e:
        print(f"⚠️ 无法获取Tesseract版本: {e}")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 测试指定的图片文件
        image_path = sys.argv[1]
        test_image_ocr(image_path)
    else:
        # 测试当前目录下的所有图片
        print("\n使用方法:")
        print("1. 测试指定图片: python test_real_image_ocr.py <图片路径>")
        print("2. 测试当前目录所有图片: python test_real_image_ocr.py")
        print("\n正在测试当前目录下的图片...")
        test_multiple_images()

if __name__ == "__main__":
    main() 