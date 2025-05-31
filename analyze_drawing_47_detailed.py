#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析图纸47 - 重点检查图框、图名和构件识别准确性
"""

import psycopg2
import json

def analyze_drawing_47_detailed():
    """详细分析图纸47的识别结果"""
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
        
        # 获取图纸47的识别结果
        cursor.execute('SELECT id, filename, file_path, recognition_results, ocr_results FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print(f"=== 图纸47详细分析 ===")
        print(f"ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"文件路径: {row[2]}")
        
        # 分析识别结果
        if row[3]:
            results = row[3]
            
            # 1. 检查图框识别
            print("\n📋 图框识别分析:")
            if 'recognition' in results:
                recognition = results['recognition']
                
                # 检查是否有图框信息
                if 'drawing_info' in recognition:
                    drawing_info = recognition['drawing_info']
                    print("✅ 找到图框信息:")
                    for key, value in drawing_info.items():
                        print(f"  {key}: {value}")
                else:
                    print("❌ 未找到图框信息")
                
                # 检查是否有图名识别
                if 'title' in recognition:
                    print(f"✅ 图名: {recognition['title']}")
                elif 'drawing_info' in recognition and 'title' in recognition['drawing_info']:
                    print(f"✅ 图名: {recognition['drawing_info']['title']}")
                else:
                    print("❌ 未找到图名")
                
                # 检查是否有比例尺
                if 'scale' in recognition:
                    print(f"✅ 比例尺: {recognition['scale']}")
                elif 'drawing_info' in recognition and 'scale' in recognition['drawing_info']:
                    print(f"✅ 比例尺: {recognition['drawing_info']['scale']}")
                else:
                    print("❌ 未找到比例尺")
            
            # 2. 检查构件识别准确性
            print("\n🔍 构件识别分析:")
            if 'recognition' in results:
                recognition = results['recognition']
                
                # 检查多层嵌套
                if 'recognition' in recognition:
                    inner_recognition = recognition['recognition']
                    if 'components' in inner_recognition:
                        components = inner_recognition['components']
                        print("发现双重嵌套的构件数据:")
                        
                        for comp_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                            if comp_type in components:
                                count = len(components[comp_type])
                                print(f"  {comp_type}: {count}个")
                                
                                # 对于柱加固图，检查是否合理
                                if comp_type == 'columns' and count > 0:
                                    print(f"    ✅ 柱子识别 - 符合柱加固图预期")
                                    # 显示前3个柱子的详细信息
                                    for i, col in enumerate(components[comp_type][:3]):
                                        bbox = col.get('bbox', [])
                                        conf = col.get('confidence', 0)
                                        dims = col.get('dimensions', {})
                                        print(f"      柱子{i+1}: 位置{bbox[:4] if len(bbox)>=4 else bbox}, 置信度{conf:.2f}, 尺寸{dims}")
                                
                                elif comp_type != 'columns' and count > 0:
                                    print(f"    ⚠️  {comp_type}识别 - 柱加固图中不应有此类构件")
                                    # 显示前2个误识别构件的详细信息
                                    for i, comp in enumerate(components[comp_type][:2]):
                                        bbox = comp.get('bbox', [])
                                        conf = comp.get('confidence', 0)
                                        dims = comp.get('dimensions', {})
                                        print(f"      误识别{i+1}: 位置{bbox[:4] if len(bbox)>=4 else bbox}, 置信度{conf:.2f}, 尺寸{dims}")
                
                # 检查直接的构件数据
                for comp_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                    if comp_type in recognition:
                        count = len(recognition[comp_type])
                        if count > 0:
                            print(f"  直接识别的{comp_type}: {count}个")
            
            # 3. 分析工程量计算
            print("\n📊 工程量计算分析:")
            if 'quantities' in results:
                quantities = results['quantities']
                total_volume = quantities.get('total', {}).get('total_volume', 0)
                print(f"总工程量: {total_volume:.3f} m³")
                
                # 对于柱加固图，主要应该是柱子的工程量
                column_volume = quantities.get('total', {}).get('column_volume', 0)
                wall_volume = quantities.get('total', {}).get('wall_volume', 0)
                beam_volume = quantities.get('total', {}).get('beam_volume', 0)
                
                print(f"柱子工程量: {column_volume:.3f} m³ ({column_volume/total_volume*100:.1f}%)" if total_volume > 0 else f"柱子工程量: {column_volume:.3f} m³")
                if wall_volume > 0:
                    print(f"⚠️  墙体工程量: {wall_volume:.3f} m³ (可能误识别)")
                if beam_volume > 0:
                    print(f"⚠️  梁工程量: {beam_volume:.3f} m³ (可能误识别)")
        
        # 4. 分析OCR结果中的图名信息
        print("\n📝 OCR文字分析:")
        if row[4]:
            ocr_results = row[4]
            
            # 处理不同格式的OCR结果
            text = ""
            if isinstance(ocr_results, dict):
                if 'text' in ocr_results:
                    text = ocr_results['text']
                elif 'result' in ocr_results:
                    text = ocr_results['result']
                else:
                    # 如果OCR结果是嵌套的dict，尝试提取文本
                    text = str(ocr_results)
            elif isinstance(ocr_results, str):
                text = ocr_results
            else:
                text = str(ocr_results)
            
            if text and isinstance(text, str):
                print("OCR识别的文字内容:")
                lines = text.split('\n')[:15]  # 显示前15行
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:
                        print(f"  {i+1}: {line}")
                        # 检查是否包含图名相关信息
                        if '柱' in line and ('加固' in line or '结构' in line or '平面' in line or '改造' in line):
                            print(f"    ✅ 可能的图名: {line}")
                        elif '图' in line and ('平面' in line or '立面' in line or '详' in line):
                            print(f"    ✅ 可能的图名: {line}")
                
                # 搜索关键词
                key_terms = ['柱', '加固', '结构', '改造', '平面图', '立面图', '详图', '1:', '比例']
                found_terms = []
                for term in key_terms:
                    if term in text:
                        found_terms.append(term)
                
                if found_terms:
                    print(f"\n找到关键词: {', '.join(found_terms)}")
                    
                    # 特别检查图名模式
                    import re
                    # 查找图名模式：通常在图纸上方或特定位置
                    title_patterns = [
                        r'.*柱.*加固.*图.*',
                        r'.*柱.*结构.*图.*',
                        r'.*改造.*加固.*图.*',
                        r'.*平面.*图.*',
                        r'.*1\s*:\s*100.*'  # 比例尺
                    ]
                    
                    for pattern in title_patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            print(f"匹配图名模式 '{pattern}': {matches}")
                else:
                    print("未找到相关关键词")
                    
                # 显示原始OCR结果的部分内容以便分析
                print(f"\nOCR结果总长度: {len(text)} 字符")
                if len(text) > 200:
                    print(f"部分内容预览: {text[:200]}...")
            else:
                print(f"OCR结果格式异常: {type(text)}")
                print(f"OCR结果内容: {ocr_results}")
        else:
            print("无OCR结果")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_drawing_47_detailed() 