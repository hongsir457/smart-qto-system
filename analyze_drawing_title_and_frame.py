#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门分析图纸47的图框和图名识别
"""

import psycopg2
import json
import re

def analyze_drawing_title_and_frame():
    """分析图纸47的图框和图名识别情况"""
    try:
        # 连接数据库
        conn = psycopg2.connect(
            host="dbconn.sealoshzh.site",
            port=48982,
            database="postgres",
            user="postgres",
            password="2xn59xgm"
        )
        cursor = conn.cursor()
        
        # 获取图纸47的OCR结果
        cursor.execute('SELECT id, filename, ocr_results FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print(f"=== 图纸47图框和图名分析 ===")
        print(f"文件名: {row[1]}")
        
        if row[2] and 'text' in row[2] and 'text' in row[2]['text']:
            ocr_text = row[2]['text']['text']
            
            print(f"\n📝 OCR文本总长度: {len(ocr_text)} 字符")
            
            # 1. 查找图名信息
            print("\n🎯 图名识别分析:")
            
            # 图名模式匹配
            title_patterns = [
                r'.*一层.*柱.*结构.*改造.*加固.*平面.*图.*',
                r'.*柱.*结构.*改造.*加固.*平面.*图.*',
                r'.*柱.*加固.*平面.*图.*',
                r'.*结构.*改造.*图.*',
                r'.*加固.*平面.*图.*'
            ]
            
            found_titles = []
            for pattern in title_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if match.strip() and match.strip() not in found_titles:
                            found_titles.append(match.strip())
            
            if found_titles:
                print("✅ 找到可能的图名:")
                for i, title in enumerate(found_titles):
                    print(f"  {i+1}. {title}")
            else:
                print("❌ 未找到明确的图名")
            
            # 2. 查找比例尺
            print("\n📏 比例尺识别:")
            scale_patterns = [
                r'1\s*:\s*100',
                r'1\s*:\s*50',
                r'1\s*:\s*200',
                r'比例.*1.*:.*\d+',
                r'scale.*1.*:.*\d+'
            ]
            
            found_scales = []
            for pattern in scale_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    found_scales.extend(matches)
            
            if found_scales:
                print("✅ 找到比例尺:")
                for scale in set(found_scales):
                    print(f"  - {scale}")
            else:
                print("❌ 未找到比例尺")
            
            # 3. 查找图框信息
            print("\n📋 图框识别:")
            
            # 查找图纸编号
            drawing_number_patterns = [
                r'[A-Z]*\d+-\d+',
                r'图.*号.*[:：]\s*([A-Z]*\d+-\d+)',
                r'Drawing.*No.*[:：]\s*([A-Z]*\d+-\d+)'
            ]
            
            found_numbers = []
            for pattern in drawing_number_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    found_numbers.extend(matches)
            
            if found_numbers:
                print("✅ 找到图纸编号:")
                for num in set(found_numbers):
                    print(f"  - {num}")
            else:
                print("❌ 未找到图纸编号")
            
            # 4. 查找设计单位
            print("\n🏢 设计单位识别:")
            company_patterns = [
                r'上海.*安装.*工程.*集团',
                r'SHANGHAI.*INSTALLATION.*ENGINEERING.*GROUP',
                r'设计.*单位.*[:：]\s*([^\\n]+)',
                r'Design.*Unit.*[:：]\s*([^\\n]+)'
            ]
            
            found_companies = []
            for pattern in company_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    if isinstance(matches[0], tuple):
                        found_companies.extend([m for m in matches[0] if m.strip()])
                    else:
                        found_companies.extend(matches)
            
            if found_companies:
                print("✅ 找到设计单位:")
                for company in set(found_companies):
                    print(f"  - {company}")
            else:
                print("❌ 未找到设计单位")
            
            # 5. 构件类型识别验证
            print("\n🔍 构件识别验证:")
            
            # 查找柱子相关信息
            column_patterns = [
                r'K-[A-Z]*\d+.*\d+x\d+',  # 柱编号和尺寸
                r'柱.*\d+.*x.*\d+',        # 中文柱描述
                r'\d+x\d+.*柱',            # 尺寸加柱
                r'Column.*\d+x\d+'         # 英文柱描述
            ]
            
            found_columns = []
            for pattern in column_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    found_columns.extend(matches)
            
            print(f"柱子相关信息: {len(found_columns)}项")
            if found_columns:
                for i, col in enumerate(found_columns[:5]):  # 显示前5个
                    print(f"  {i+1}. {col}")
                if len(found_columns) > 5:
                    print(f"  ... 还有 {len(found_columns) - 5} 项")
            
            # 查找是否有墙、梁等不应该出现的构件
            unwanted_patterns = [
                r'墙.*\d+.*x.*\d+',
                r'W-[A-Z]*\d+',     # 墙编号
                r'B-[A-Z]*\d+',     # 梁编号
                r'梁.*\d+.*x.*\d+',
                r'Wall.*\d+x\d+',
                r'Beam.*\d+x\d+'
            ]
            
            unwanted_found = []
            for pattern in unwanted_patterns:
                matches = re.findall(pattern, ocr_text, re.IGNORECASE)
                if matches:
                    unwanted_found.extend(matches)
            
            if unwanted_found:
                print(f"⚠️  发现非柱构件信息: {len(unwanted_found)}项")
                for i, item in enumerate(unwanted_found[:3]):
                    print(f"  {i+1}. {item}")
            else:
                print("✅ 未发现不应有的构件信息")
            
            # 6. 分析关键字密度
            print("\n📊 关键字密度分析:")
            keywords = {
                '柱': ocr_text.count('柱'),
                '加固': ocr_text.count('加固'),
                '结构': ocr_text.count('结构'),
                '改造': ocr_text.count('改造'),
                'K-': ocr_text.count('K-'),  # 柱编号前缀
                '墙': ocr_text.count('墙'),
                '梁': ocr_text.count('梁'),
                '基础': ocr_text.count('基础')
            }
            
            for keyword, count in keywords.items():
                if count > 0:
                    print(f"  '{keyword}': {count} 次")
            
            # 显示OCR文本的开头和结尾部分
            print(f"\n📋 OCR文本样本:")
            print("开头部分:")
            print(ocr_text[:300] + "..." if len(ocr_text) > 300 else ocr_text)
            
            if len(ocr_text) > 600:
                print("\n结尾部分:")
                print("..." + ocr_text[-300:])
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_drawing_title_and_frame() 