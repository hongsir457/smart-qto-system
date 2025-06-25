#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR JSON 转 Markdown 转换器
将OCR识别结果JSON文件转换为结构化的Markdown文档
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

def convert_ocr_json_to_markdown(json_file_path: str, output_file_path: str = None) -> str:
    """
    将OCR JSON文件转换为Markdown格式
    
    Args:
        json_file_path: OCR JSON文件路径
        output_file_path: 输出Markdown文件路径（可选）
        
    Returns:
        str: Markdown内容
    """
    
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    # 提取数据
    meta = ocr_data.get('meta', {})
    processing_info = ocr_data.get('processing_info', {})
    raw_texts = ocr_data.get('raw_texts', [])
    summary = ocr_data.get('summary', {})
    
    # 开始构建Markdown内容
    markdown_lines = []
    
    # 标题和元数据
    markdown_lines.append("---")
    markdown_lines.append("title: 建筑图纸OCR识别结果")
    markdown_lines.append(f"source_image: {os.path.basename(meta.get('source_image', '未知'))}")
    markdown_lines.append(f"ocr_time: {meta.get('ocr_time', '未知')}")
    markdown_lines.append(f"ocr_engine: {meta.get('ocr_engine', '未知')}")
    markdown_lines.append(f"total_texts: {processing_info.get('total_texts', 0)}")
    markdown_lines.append(f"processing_time: {processing_info.get('processing_time', 0)}s")
    markdown_lines.append("---")
    markdown_lines.append("")
    
    # 主标题
    markdown_lines.append("# 建筑图纸OCR识别结果")
    markdown_lines.append("")
    
    # 基本信息
    markdown_lines.append("## 📋 基本信息")
    markdown_lines.append(f"- **OCR引擎**: {meta.get('ocr_engine', '未知')}")
    markdown_lines.append(f"- **识别时间**: {meta.get('ocr_time', '未知')}")
    markdown_lines.append(f"- **图片来源**: `{os.path.basename(meta.get('source_image', '未知'))}`")
    markdown_lines.append(f"- **识别文本数量**: {processing_info.get('total_texts', 0)} 个")
    markdown_lines.append(f"- **处理耗时**: {processing_info.get('processing_time', 0)} 秒")
    markdown_lines.append(f"- **处理状态**: {processing_info.get('status', '未知')}")
    markdown_lines.append("")
    
    # 统计信息
    if summary:
        stats = summary.get('statistics', {})
        markdown_lines.append("## 📊 识别统计")
        markdown_lines.append(f"- **总文本数**: {stats.get('total_count', 0)}")
        markdown_lines.append(f"- **数字类文本**: {stats.get('numeric_count', 0)}")
        markdown_lines.append(f"- **构件编号**: {stats.get('component_code_count', 0)}")
        markdown_lines.append(f"- **尺寸规格**: {stats.get('dimension_count', 0)}")
        markdown_lines.append(f"- **平均置信度**: {stats.get('avg_confidence', 0):.2f}")
        markdown_lines.append("")
    
    # 按类型分类显示文本
    if raw_texts:
        # 分类文本
        component_codes = []
        numbers = []
        dimensions = []
        other_texts = []
        
        for item in raw_texts:
            text = item.get('text', '').strip()
            confidence = item.get('confidence', 0)
            
            if not text:
                continue
                
            if item.get('is_component_code'):
                component_codes.append((text, confidence))
            elif item.get('is_number'):
                numbers.append((text, confidence))
            elif item.get('is_dimension'):
                dimensions.append((text, confidence))
            else:
                # 识别一些关键信息
                if any(keyword in text for keyword in ['K-', 'KZ', 'KL', 'Q-', 'B-']):
                    component_codes.append((text, confidence))
                elif text.isdigit() or any(char.isdigit() for char in text):
                    numbers.append((text, confidence))
                else:
                    other_texts.append((text, confidence))
        
        # 构件编号
        if component_codes:
            markdown_lines.append("## 🏗️ 构件编号")
            markdown_lines.append("| 编号 | 置信度 |")
            markdown_lines.append("|------|--------|")
            for text, confidence in sorted(component_codes, key=lambda x: x[0]):
                markdown_lines.append(f"| {text} | {confidence:.3f} |")
            markdown_lines.append("")
        
        # 数值信息
        if numbers:
            markdown_lines.append("## 🔢 数值信息")
            markdown_lines.append("| 数值 | 置信度 | 类型推测 |")
            markdown_lines.append("|------|--------|----------|")
            for text, confidence in sorted(numbers, key=lambda x: -x[1]):  # 按置信度降序
                # 推测数值类型
                value_type = "未知"
                if len(text) == 4 and text.isdigit():
                    value_type = "尺寸(mm)"
                elif len(text) >= 5 and text.isdigit():
                    value_type = "编号/坐标"
                elif 'x' in text.lower() or '×' in text:
                    value_type = "尺寸规格"
                
                markdown_lines.append(f"| {text} | {confidence:.3f} | {value_type} |")
            markdown_lines.append("")
        
        # 尺寸规格
        if dimensions:
            markdown_lines.append("## 📏 尺寸规格")
            markdown_lines.append("| 尺寸 | 置信度 |")
            markdown_lines.append("|------|--------|")
            for text, confidence in dimensions:
                markdown_lines.append(f"| {text} | {confidence:.3f} |")
            markdown_lines.append("")
        
        # 其他重要信息
        if other_texts:
            # 进一步分类其他文本
            project_info = []
            design_info = []
            general_info = []
            
            for text, confidence in other_texts:
                if any(keyword in text for keyword in ['楼', '层', '图', '表', '平面']):
                    project_info.append((text, confidence))
                elif any(keyword in text for keyword in ['设计', '制图', '阶段']) or len(text) <= 3 and confidence > 0.8:
                    design_info.append((text, confidence))
                else:
                    general_info.append((text, confidence))
            
            # 项目信息
            if project_info:
                markdown_lines.append("## 📋 项目信息")
                for text, confidence in sorted(project_info, key=lambda x: -x[1]):
                    markdown_lines.append(f"- **{text}** (置信度: {confidence:.3f})")
                markdown_lines.append("")
            
            # 设计信息
            if design_info:
                markdown_lines.append("## 👨‍💼 设计信息")
                for text, confidence in sorted(design_info, key=lambda x: -x[1]):
                    markdown_lines.append(f"- **{text}** (置信度: {confidence:.3f})")
                markdown_lines.append("")
            
            # 其他信息
            if general_info:
                markdown_lines.append("## 📝 其他信息")
                for text, confidence in sorted(general_info, key=lambda x: -x[1]):
                    markdown_lines.append(f"- {text} (置信度: {confidence:.3f})")
                markdown_lines.append("")
    
    # 完整文本列表（按位置排序）
    markdown_lines.append("## 📄 完整文本列表")
    markdown_lines.append("*按在图纸中的位置排序*")
    markdown_lines.append("")
    markdown_lines.append("| 序号 | 文本内容 | 置信度 | 类型 | 位置(x,y) |")
    markdown_lines.append("|------|----------|--------|------|-----------|")
    
    for i, item in enumerate(raw_texts, 1):
        text = item.get('text', '').replace('|', '\\|')  # 转义表格分隔符
        confidence = item.get('confidence', 0)
        
        # 确定类型
        item_type = "文本"
        if item.get('is_component_code'):
            item_type = "构件编号"
        elif item.get('is_number'):
            item_type = "数值"
        elif item.get('is_dimension'):
            item_type = "尺寸"
        
        # 获取位置
        bbox = item.get('bbox', {})
        if isinstance(bbox, dict):
            x = bbox.get('center_x', 0)
            y = bbox.get('center_y', 0)
            position = f"({x:.0f},{y:.0f})"
        else:
            position = "未知"
        
        markdown_lines.append(f"| {i} | {text} | {confidence:.3f} | {item_type} | {position} |")
    
    markdown_lines.append("")
    
    # 处理说明
    markdown_lines.append("## ℹ️ 处理说明")
    markdown_lines.append("- 本文档由OCR自动识别生成")
    markdown_lines.append("- 置信度范围：0.0-1.0，数值越高表示识别越准确")
    markdown_lines.append("- 文本类型由系统自动推测，可能存在误判")
    markdown_lines.append("- 建议结合原图进行人工校验")
    markdown_lines.append("")
    
    # 技术信息
    markdown_lines.append("---")
    markdown_lines.append("*生成时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*")
    
    # 合并所有行
    markdown_content = "\n".join(markdown_lines)
    
    # 如果指定了输出文件路径，则保存文件
    if output_file_path:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"✅ Markdown文件已保存到: {output_file_path}")
    
    return markdown_content

def main():
    """主函数：处理命令行参数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python convert_ocr_to_markdown.py <json_file_path> [output_file_path]")
        print("示例: python convert_ocr_to_markdown.py ocr_result.json output.md")
        return
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_file):
        print(f"❌ 文件不存在: {json_file}")
        return
    
    try:
        markdown_content = convert_ocr_json_to_markdown(json_file, output_file)
        
        if not output_file:
            # 如果没有指定输出文件，则打印到控制台
            print("📄 生成的Markdown内容:")
            print("=" * 60)
            print(markdown_content)
        
    except Exception as e:
        print(f"❌ 转换失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 