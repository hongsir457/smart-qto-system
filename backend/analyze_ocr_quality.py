#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR质量分析工具
分析OCR识别结果的准确性、完整性和可用性
"""

import sys
import os
import re
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.services.drawing import extract_text

def analyze_ocr_quality(image_path, expected_keywords=None):
    """
    分析OCR识别质量
    
    Args:
        image_path: 图片路径
        expected_keywords: 期望识别的关键词列表
    """
    print("🔍 OCR质量分析工具")
    print("=" * 80)
    print(f"📁 分析图片: {image_path}")
    print("=" * 80)
    
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    # 执行OCR识别
    print("\n🔧 执行OCR识别...")
    start_time = time.time()
    
    try:
        result = extract_text(image_path)
        processing_time = time.time() - start_time
        
        # 适配extract_text的返回格式
        if result and isinstance(result, dict):
            if "text" in result:
                # 成功识别
                text = result.get('text', '')
                print(f"✅ OCR识别成功")
                print(f"⏱️ 处理时间: {processing_time:.2f} 秒")
                print(f"📝 识别字符数: {len(text)} 字符")
                
                # 分析识别质量
                analyze_text_quality(text, expected_keywords)
                
            elif "error" in result:
                # 识别失败
                print(f"❌ OCR识别失败: {result.get('error', '未知错误')}")
                
            elif "warning" in result:
                # 有警告但可能有部分结果
                print(f"⚠️ OCR识别警告: {result.get('warning', '未知警告')}")
                text = result.get('text', '')
                if text:
                    analyze_text_quality(text, expected_keywords)
                    
        else:
            print(f"❌ OCR识别返回格式异常: {type(result)}")
            
    except Exception as e:
        print(f"❌ OCR识别异常: {str(e)}")
        import traceback
        traceback.print_exc()

def analyze_text_quality(text, expected_keywords=None):
    """分析文本质量"""
    print("\n📊 文本质量分析")
    print("-" * 50)
    
    # 1. 基本统计
    lines = text.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    
    print(f"📄 总行数: {len(lines)}")
    print(f"📝 非空行数: {len(non_empty_lines)}")
    print(f"📊 平均行长度: {sum(len(line) for line in non_empty_lines) / len(non_empty_lines) if non_empty_lines else 0:.1f} 字符")
    
    # 2. 数字识别分析
    numbers = re.findall(r'\d+', text)
    dimensions = re.findall(r'\d+\s*[xX×]\s*\d+', text)
    areas = re.findall(r'\d+\.?\d*\s*m²', text)
    
    print(f"\n🔢 数字识别:")
    print(f"   - 数字总数: {len(numbers)}")
    print(f"   - 尺寸标注: {len(dimensions)} 个")
    print(f"   - 面积标注: {len(areas)} 个")
    
    if dimensions:
        print(f"   - 尺寸示例: {dimensions[:3]}")
    if areas:
        print(f"   - 面积示例: {areas[:3]}")
    
    # 3. 关键词识别分析
    if expected_keywords:
        print(f"\n🎯 关键词识别分析:")
        found_keywords = []
        missing_keywords = []
        
        for keyword in expected_keywords:
            if keyword.lower() in text.lower():
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        recognition_rate = len(found_keywords) / len(expected_keywords) * 100
        print(f"   - 识别率: {recognition_rate:.1f}% ({len(found_keywords)}/{len(expected_keywords)})")
        
        if found_keywords:
            print(f"   - 已识别: {', '.join(found_keywords)}")
        if missing_keywords:
            print(f"   - 未识别: {', '.join(missing_keywords)}")
    
    # 4. 文本质量评估
    print(f"\n📈 文本质量评估:")
    
    # 计算可读性
    readable_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in '.,:-()[]{}')
    readability = readable_chars / len(text) * 100 if text else 0
    print(f"   - 可读性: {readability:.1f}%")
    
    # 计算信息密度
    info_density = len(non_empty_lines) / len(text) * 1000 if text else 0
    print(f"   - 信息密度: {info_density:.2f} 行/千字符")
    
    # 5. 常见错误分析
    print(f"\n⚠️ 常见识别错误:")
    
    # 检查常见OCR错误
    common_errors = {
        'O和0混淆': len(re.findall(r'[A-Z]0|0[A-Z]', text)),
        'I和1混淆': len(re.findall(r'[A-Z]1|1[A-Z]', text)),
        '特殊字符错误': len(re.findall(r'[^\w\s\d.,:\-()[\]{}×xX²]', text)),
        '空格异常': len(re.findall(r'\s{3,}', text))
    }
    
    error_found = False
    for error_type, count in common_errors.items():
        if count > 0:
            print(f"   - {error_type}: {count} 处")
            error_found = True
    
    if not error_found:
        print("   - 未发现明显错误")
    
    # 6. 建筑图纸特定分析
    print(f"\n🏗️ 建筑图纸特定分析:")
    
    # 房间识别
    room_keywords = ['room', 'kitchen', 'bathroom', 'bedroom', 'living', 'balcony']
    found_rooms = [kw for kw in room_keywords if kw.lower() in text.lower()]
    print(f"   - 识别房间: {len(found_rooms)} 个 ({', '.join(found_rooms)})")
    
    # 材料规格
    material_keywords = ['concrete', 'wall', 'floor', 'ceiling', 'thickness', 'mm']
    found_materials = [kw for kw in material_keywords if kw.lower() in text.lower()]
    print(f"   - 材料信息: {len(found_materials)} 项")
    
    # 图纸信息
    drawing_keywords = ['scale', 'drawing', 'project', 'date', 'plan']
    found_drawing_info = [kw for kw in drawing_keywords if kw.lower() in text.lower()]
    print(f"   - 图纸信息: {len(found_drawing_info)} 项")
    
    # 7. 质量评分
    print(f"\n⭐ 总体质量评分:")
    
    # 计算综合评分
    keyword_score = len(found_keywords) / len(expected_keywords) * 100 if expected_keywords else 80
    content_score = min(100, len(non_empty_lines) * 5)  # 每行5分，最高100分
    readability_score = readability
    
    overall_score = (keyword_score * 0.4 + content_score * 0.3 + readability_score * 0.3)
    
    print(f"   - 关键词识别: {keyword_score:.1f}/100")
    print(f"   - 内容丰富度: {content_score:.1f}/100")
    print(f"   - 文本可读性: {readability_score:.1f}/100")
    print(f"   - 综合评分: {overall_score:.1f}/100")
    
    # 评级
    if overall_score >= 90:
        grade = "优秀 🌟"
    elif overall_score >= 80:
        grade = "良好 👍"
    elif overall_score >= 70:
        grade = "中等 👌"
    elif overall_score >= 60:
        grade = "及格 ✅"
    else:
        grade = "需改进 ⚠️"
    
    print(f"   - 质量等级: {grade}")
    
    # 8. 显示完整识别结果
    print(f"\n📋 完整识别结果:")
    print("-" * 50)
    print(text)
    print("-" * 50)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python analyze_ocr_quality.py <图片路径> [关键词1,关键词2,...]")
        print("示例: python analyze_ocr_quality.py demo_building_plan.png")
        print("示例: python analyze_ocr_quality.py complex_building_plan.png LIVING,KITCHEN,BEDROOM")
        return
    
    image_path = sys.argv[1]
    
    # 解析期望关键词
    expected_keywords = None
    if len(sys.argv) > 2:
        expected_keywords = [kw.strip() for kw in sys.argv[2].split(',')]
    
    # 默认建筑图纸关键词
    if not expected_keywords:
        expected_keywords = [
            'LIVING ROOM', 'KITCHEN', 'BEDROOM', 'BATHROOM', 
            'BALCONY', 'PLAN', 'SCALE', 'AREA', 'PROJECT'
        ]
    
    analyze_ocr_quality(image_path, expected_keywords)

if __name__ == "__main__":
    main() 