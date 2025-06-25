#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR文本格式化演示 - 展示原始数据到可读文本的转换过程
"""

import re
from datetime import datetime

def demo_ocr_text_formatting():
    """演示OCR文本格式化功能"""
    
    print("🎯 OCR文本格式化演示")
    print("=" * 60)
    
    # 1. 模拟PaddleOCR原始结果
    print("📥 1. PaddleOCR原始识别结果:")
    raw_ocr_texts = [
        "KZI",      # 构件编号(错误：I应该是1)
        "LLO",      # 构件编号(错误：O应该是0) 
        "400*600",  # 尺寸规格(错误：*应该是×)
        "C2O",      # 材料规格(错误：O应该是0)
        "曲阳路930号项目",  # 项目信息
        "一层柱结构改造平面图"  # 图纸信息
    ]
    
    for i, text in enumerate(raw_ocr_texts):
        print(f"  [{i+1}] {text}")
    
    print()
    
    # 2. 智能纠错过程
    print("🔧 2. 智能纠错过程:")
    ocr_corrections = {
        "KZI": "KZ1",  "LLI": "LL1",  "KZO": "KZ0",  "LLO": "LL0",
        "C2O": "C20",  "C3O": "C30",  "C4O": "C40"
    }
    
    corrected_texts = []
    for text in raw_ocr_texts:
        corrected = text
        
        # 基础纠错
        for wrong, correct in ocr_corrections.items():
            corrected = corrected.replace(wrong, correct)
        
        # 尺寸格式纠错
        corrected = re.sub(r"(\d+)\s*[\*Xx]\s*(\d+)", r"\1×\2", corrected)
        
        corrected_texts.append(corrected)
        
        if text != corrected:
            print(f"  ✅ {text} -> {corrected}")
        else:
            print(f"  ➡️ {text} (无需纠错)")
    
    print()
    
    # 3. 智能分类过程  
    print("📋 3. 智能分类结果:")
    
    classified_content = {
        'component_codes': [],
        'dimensions': [],
        'materials': [],
        'project_info': [],
        'drawing_info': []
    }
    
    for text in corrected_texts:
        confidence = 0.95  # 模拟置信度
        
        if re.match(r'^[A-Z]+\d+$', text):  # 构件编号
            classified_content['component_codes'].append({
                'text': text, 'confidence': confidence
            })
            print(f"  🔧 构件编号: {text}")
            
        elif re.match(r'\d+×\d+', text):  # 尺寸规格
            classified_content['dimensions'].append({
                'text': text, 'confidence': confidence
            })
            print(f"  📏 尺寸规格: {text}")
            
        elif 'C2' in text or 'C3' in text:  # 材料规格
            classified_content['materials'].append({
                'text': text, 'confidence': confidence
            })
            print(f"  🧱 材料规格: {text}")
            
        elif '项目' in text or '工程' in text:  # 项目信息
            classified_content['project_info'].append({
                'text': text, 'confidence': confidence
            })
            print(f"  🏗️ 项目信息: {text}")
            
        elif '平面图' in text or '图' in text:  # 图纸信息
            classified_content['drawing_info'].append({
                'text': text, 'confidence': confidence
            })
            print(f"  📐 图纸信息: {text}")
    
    print()
    
    # 4. 生成可读文本报告
    print("📄 4. 生成可读文本报告:")
    print("=" * 50)
    
    readable_text = generate_readable_report(classified_content)
    print(readable_text)
    
    print("=" * 50)
    
    # 5. 前端展示方式
    print("🖥️ 5. 前端展示方式:")
    print("  标签页1: 📋 可读文本")
    print("    - 上述文本报告，支持复制")
    print("    - 等宽字体，格式整齐")
    print("    - 一键复制到剪贴板")
    print()
    print("  标签页2: ⚙️ 结构化数据") 
    print("    - 原有的卡片式展示")
    print("    - 分类详细，交互丰富")
    print("    - 置信度可视化")
    
    print()
    print("🎉 演示完成！这就是从原始OCR到可读文本的完整转换过程。")

def generate_readable_report(classified_content):
    """生成可读文本报告"""
    
    lines = []
    
    lines.append("📋 OCR识别结果报告")
    lines.append("=" * 50)
    lines.append("")
    
    # 基本统计
    total_items = sum(len(items) for items in classified_content.values())
    lines.append("📊 基本信息")
    lines.append("-" * 20)
    lines.append(f"处理时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    lines.append(f"识别文本总数: {total_items} 项")
    lines.append(f"平均置信度: 95.0%")
    lines.append("")
    
    # 项目信息
    if classified_content['project_info']:
        lines.append("🏗️ 项目信息")
        lines.append("-" * 20)
        for item in classified_content['project_info']:
            lines.append(f"项目名称: {item['text']}")
        lines.append("")
    
    # 图纸信息
    if classified_content['drawing_info']:
        lines.append("📐 图纸信息") 
        lines.append("-" * 20)
        for item in classified_content['drawing_info']:
            lines.append(f"图纸名称: {item['text']}")
        lines.append("")
    
    # 构件识别结果
    if classified_content['component_codes']:
        lines.append("🔧 构件识别结果")
        lines.append("-" * 20)
        lines.append(f"共识别到 {len(classified_content['component_codes'])} 个构件编号:")
        
        for item in classified_content['component_codes']:
            confidence_text = f"(置信度:{item['confidence']:.1%})"
            lines.append(f"  - {item['text']} {confidence_text}")
        lines.append("")
    
    # 尺寸信息
    if classified_content['dimensions']:
        lines.append("📏 尺寸信息")
        lines.append("-" * 20)
        lines.append(f"共识别到 {len(classified_content['dimensions'])} 个尺寸规格:")
        
        for item in classified_content['dimensions']:
            confidence_text = f"(置信度:{item['confidence']:.1%})"
            lines.append(f"  - {item['text']} {confidence_text}")
        lines.append("")
    
    # 材料信息
    if classified_content['materials']:
        lines.append("🧱 材料信息")
        lines.append("-" * 20)
        lines.append(f"共识别到 {len(classified_content['materials'])} 个材料规格:")
        
        for item in classified_content['materials']:
            confidence_text = f"(置信度:{item['confidence']:.1%})"
            lines.append(f"  - {item['text']} {confidence_text}")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 50)
    
    return "\n".join(lines)

if __name__ == "__main__":
    demo_ocr_text_formatting() 