#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR优化建议工具
基于识别结果分析，提供具体的优化建议和解决方案
"""

import sys
import os
import re
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.services.drawing import extract_text

def analyze_and_suggest_optimizations(image_path):
    """
    分析OCR结果并提供优化建议
    """
    print("🔧 OCR优化建议工具")
    print("=" * 80)
    print(f"📁 分析图片: {image_path}")
    print("=" * 80)
    
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    # 执行OCR识别
    try:
        result = extract_text(image_path)
        
        if result and "text" in result:
            text = result.get('text', '')
            print(f"✅ OCR识别成功，识别了 {len(text)} 个字符")
            
            # 分析问题并提供建议
            analyze_issues_and_suggest(text)
            
        elif "error" in result:
            print(f"❌ OCR识别失败: {result.get('error')}")
            suggest_error_solutions()
            
    except Exception as e:
        print(f"❌ 分析异常: {str(e)}")

def analyze_issues_and_suggest(text):
    """分析识别问题并提供优化建议"""
    
    print("\n🔍 问题诊断与优化建议")
    print("=" * 50)
    
    issues_found = []
    suggestions = []
    
    # 1. 字符识别错误分析
    print("1️⃣ 字符识别错误分析")
    print("-" * 30)
    
    # 检查常见错误模式
    char_errors = {
        '面积单位错误': re.findall(r'm\?\?|m\?\?|m\?\?', text),
        '拼写错误': find_spelling_errors(text),
        '数字字母混淆': re.findall(r'\d+[|l]\w+|\w+[|l]\d+', text),
        '特殊符号错误': re.findall(r'[^\w\s\d.,:\-()[\]{}×xX²]', text)
    }
    
    for error_type, errors in char_errors.items():
        if errors:
            print(f"   ❌ {error_type}: {len(errors)} 处")
            issues_found.append(error_type)
            if error_type == '面积单位错误':
                suggestions.append("建议：在后处理中添加 'm??' → 'm²' 的替换规则")
            elif error_type == '拼写错误':
                suggestions.append("建议：使用拼写检查库或建立建筑术语词典进行纠错")
            elif error_type == '数字字母混淆':
                suggestions.append("建议：优化OCR配置，使用更严格的字符分类")
    
    if not any(char_errors.values()):
        print("   ✅ 字符识别质量良好")
    
    # 2. 结构化信息提取分析
    print("\n2️⃣ 结构化信息提取分析")
    print("-" * 30)
    
    # 检查关键信息提取
    dimensions = re.findall(r'\d+\s*[xX×]\s*\d+', text)
    areas = re.findall(r'Area:\s*[\d.]+\s*m', text)
    rooms = re.findall(r'(LIVING ROOM|BEDROOM|KITCHEN|BATHROOM|BALCONY)', text, re.IGNORECASE)
    
    print(f"   📐 尺寸信息: {len(dimensions)} 个")
    print(f"   📏 面积信息: {len(areas)} 个")
    print(f"   🏠 房间信息: {len(rooms)} 个")
    
    if len(dimensions) < 3:
        issues_found.append("尺寸信息不足")
        suggestions.append("建议：优化数字和符号识别，特别是 'x' 和 '×' 符号")
    
    if len(areas) < 3:
        issues_found.append("面积信息不足")
        suggestions.append("建议：改进 'Area:' 关键词周围的文本识别")
    
    # 3. 图像质量评估
    print("\n3️⃣ 图像质量评估")
    print("-" * 30)
    
    # 基于识别结果推断图像质量问题
    text_density = len(text.replace(' ', '').replace('\n', '')) / len(text) if text else 0
    line_count = len([line for line in text.split('\n') if line.strip()])
    
    print(f"   📊 文本密度: {text_density:.2f}")
    print(f"   📄 有效行数: {line_count}")
    
    if text_density < 0.7:
        issues_found.append("文本密度低")
        suggestions.append("建议：检查图像分辨率，考虑提高DPI或使用图像增强")
    
    if line_count < 10:
        issues_found.append("识别内容少")
        suggestions.append("建议：检查图像对比度和清晰度，可能需要预处理")
    
    # 4. 生成具体优化方案
    print("\n🚀 具体优化方案")
    print("=" * 50)
    
    if issues_found:
        print("基于发现的问题，建议采取以下优化措施：\n")
        
        # 短期优化（后处理改进）
        print("📋 短期优化（后处理改进）：")
        short_term = [
            "1. 添加常见错误替换规则：m?? → m²",
            "2. 建立建筑术语词典，自动纠正拼写错误",
            "3. 优化数字和字母的分离算法",
            "4. 增强特殊符号的识别准确性"
        ]
        for item in short_term:
            print(f"   {item}")
        
        # 中期优化（算法改进）
        print("\n🔧 中期优化（算法改进）：")
        medium_term = [
            "1. 调整OCR引擎参数，优化建筑图纸识别",
            "2. 实现多种OCR方法的结果融合",
            "3. 添加基于上下文的错误纠正",
            "4. 优化图像预处理流程"
        ]
        for item in medium_term:
            print(f"   {item}")
        
        # 长期优化（深度学习）
        print("\n🤖 长期优化（AI增强）：")
        long_term = [
            "1. 训练专门的建筑图纸OCR模型",
            "2. 集成大语言模型进行智能纠错",
            "3. 实现图像质量自动评估和优化",
            "4. 开发建筑图纸专用的文本理解模型"
        ]
        for item in long_term:
            print(f"   {item}")
            
    else:
        print("🎉 当前OCR质量良好，建议保持现有配置！")
    
    # 5. 立即可实施的改进代码
    print("\n💻 立即可实施的改进代码")
    print("=" * 50)
    
    print("可以在后处理函数中添加以下改进：")
    print("""
def enhanced_post_process(text):
    '''增强的后处理函数'''
    if not text:
        return ""
    
    # 1. 常见错误替换
    replacements = {
        'm??': 'm²',
        'm？？': 'm²',
        'KITGHEN': 'KITCHEN',
        'BATHRQOM': 'BATHROOM',
        '|': 'I',  # 竖线替换为I
        '0': 'O',  # 在特定上下文中
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 2. 修复尺寸格式
    text = re.sub(r'(\d+)\s*[|l]\s*(\d+)', r'\\1 x \\2', text)
    
    # 3. 清理多余空格
    text = re.sub(r'\s{3,}', ' ', text)
    
    # 4. 修复面积格式
    text = re.sub(r'Area:\s*([\\d.]+)\s*m[^²]*', r'Area: \\1 m²', text)
    
    return text
""")

def find_spelling_errors(text):
    """查找可能的拼写错误"""
    # 建筑相关的常见词汇
    correct_words = {
        'KITCHEN', 'BATHROOM', 'BEDROOM', 'LIVING', 'ROOM', 
        'BALCONY', 'PLAN', 'SCALE', 'AREA', 'PROJECT',
        'ARCHITECTURAL', 'FLOOR', 'DRAWING', 'BUILDING'
    }
    
    # 查找可能的错误
    words = re.findall(r'[A-Z]{3,}', text)
    errors = []
    
    for word in words:
        if word not in correct_words:
            # 检查是否是常见错误
            if 'KITGHEN' in word or 'BATHRQOM' in word:
                errors.append(word)
    
    return errors

def suggest_error_solutions():
    """当OCR完全失败时提供解决建议"""
    print("\n🆘 OCR失败解决方案")
    print("=" * 50)
    
    solutions = [
        "1. 检查图像文件是否损坏或格式不支持",
        "2. 确认Tesseract OCR引擎已正确安装",
        "3. 检查图像分辨率是否过低（建议≥300DPI）",
        "4. 验证图像对比度是否足够",
        "5. 尝试转换图像格式（如PDF→PNG）",
        "6. 检查图像是否包含可识别的文字内容",
        "7. 考虑使用AI OCR服务作为备选方案"
    ]
    
    for solution in solutions:
        print(f"   {solution}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python ocr_optimization_suggestions.py <图片路径>")
        print("示例: python ocr_optimization_suggestions.py complex_building_plan.png")
        return
    
    image_path = sys.argv[1]
    analyze_and_suggest_optimizations(image_path)

if __name__ == "__main__":
    main() 