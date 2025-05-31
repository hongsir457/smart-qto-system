#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图纸46的工程量计算
"""

import psycopg2
import json
from datetime import datetime

def test_drawing_46_quantity():
    """测试图纸46的工程量计算"""
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
        
        # 获取图纸46的信息
        cursor.execute('''
            SELECT id, filename, file_path, recognition_results, ocr_results, 
                   created_at, updated_at, status
            FROM drawings WHERE id = 46
        ''')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸46")
            return
        
        print("=" * 80)
        print("图纸46工程量计算测试")
        print("=" * 80)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"图纸ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"文件路径: {row[2]}")
        print(f"创建时间: {row[5]}")
        print(f"更新时间: {row[6]}")
        print(f"处理状态: {row[7]}")
        print()
        
        # 分析识别结果
        recognition_results = row[3]
        if recognition_results:
            print("🔍 识别结果分析:")
            print("-" * 50)
            
            # 检查原始识别结果
            if 'recognition' in recognition_results:
                original_recognition = recognition_results['recognition']
                print("原始识别结果:")
                
                total_components = 0
                for component_type, data in original_recognition.items():
                    if isinstance(data, list):
                        count = len(data)
                        total_components += count
                        print(f"  {component_type}: {count}个")
                        
                        # 显示前2个构件的详细信息
                        if count > 0 and len(data) > 0:
                            for i, comp in enumerate(data[:2]):
                                if isinstance(comp, dict):
                                    bbox = comp.get('bbox', [])
                                    conf = comp.get('confidence', 0)
                                    dims = comp.get('dimensions', {})
                                    print(f"    样例{i+1}: 位置{bbox[:4] if len(bbox)>=4 else bbox}, 置信度{conf:.2f}, 尺寸{dims}")
                    else:
                        print(f"  {component_type}: {data}")
                
                print(f"\n总识别构件数: {total_components}个")
            
            # 检查转换后结果
            if 'converted' in recognition_results:
                converted_results = recognition_results['converted']
                print("\n转换后结果:")
                
                total_converted = 0
                for component_type, components in converted_results.items():
                    if isinstance(components, list):
                        count = len(components)
                        total_converted += count
                        print(f"  {component_type}: {count}个")
                        
                        # 显示转换后的样例
                        if count > 0:
                            sample = components[0] if components else {}
                            print(f"    样例: {sample}")
                    else:
                        print(f"  {component_type}: {components}")
                
                print(f"\n总转换构件数: {total_converted}个")
            
            # 检查工程量计算结果
            if 'quantities' in recognition_results:
                quantity_results = recognition_results['quantities']
                print("\n📊 工程量计算结果:")
                print("-" * 50)
                
                total_volume = 0
                component_volumes = {}
                
                for component_type, data in quantity_results.items():
                    if component_type == 'total':
                        if isinstance(data, dict):
                            total_vol = data.get('total_volume', 0) or data.get('volume', 0)
                            print(f"总工程量: {total_vol:.3f} m³")
                        else:
                            print(f"总工程量: {data}")
                    else:
                        if isinstance(data, dict):
                            vol = data.get('total_volume', 0)
                            count = data.get('count', 0)
                            component_volumes[component_type] = vol
                            total_volume += vol
                            print(f"  {component_type}: {count}个, 体积: {vol:.3f} m³")
                        else:
                            print(f"  {component_type}: {data}")
                
                print(f"\n计算总体积: {total_volume:.3f} m³")
                
                # 检查是否存在体积为0的异常
                if total_volume == 0 and total_components > 0:
                    print("⚠️  警告: 识别到构件但工程量为0，可能存在计算问题")
                elif total_volume > 0:
                    print("✅ 工程量计算正常")
                
                # 显示各构件类型占比
                if total_volume > 0:
                    print("\n构件体积占比:")
                    for comp_type, vol in component_volumes.items():
                        if vol > 0:
                            percentage = (vol / total_volume) * 100
                            print(f"  {comp_type}: {percentage:.1f}%")
            
            else:
                print("❌ 未找到工程量计算结果")
        
        else:
            print("❌ 未找到识别结果")
        
        # 检查OCR结果
        ocr_results = row[4]
        if ocr_results:
            print("\n📝 OCR结果概要:")
            print("-" * 50)
            
            if isinstance(ocr_results, dict) and 'text' in ocr_results:
                text_data = ocr_results['text']
                if isinstance(text_data, dict) and 'text' in text_data:
                    ocr_text = text_data['text']
                    print(f"OCR文本长度: {len(ocr_text)} 字符")
                    
                    # 分析图纸类型
                    keywords = ['柱', '梁', '墙', '基础', '板', '结构', '平面', '立面', '详图']
                    found_keywords = []
                    for keyword in keywords:
                        if keyword in ocr_text:
                            count = ocr_text.count(keyword)
                            found_keywords.append(f"{keyword}({count})")
                    
                    if found_keywords:
                        print(f"关键词分布: {', '.join(found_keywords)}")
                    
                    # 显示文本开头
                    print(f"文本开头: {ocr_text[:200]}...")
                else:
                    print("OCR文本格式异常")
            else:
                print("OCR结果格式异常")
        else:
            print("❌ 未找到OCR结果")
        
        # 生成建议
        print("\n💡 分析建议:")
        print("-" * 50)
        
        if recognition_results:
            if 'quantities' in recognition_results:
                quantity_results = recognition_results['quantities']
                total_vol = 0
                
                if 'total' in quantity_results:
                    total_data = quantity_results['total']
                    if isinstance(total_data, dict):
                        total_vol = total_data.get('total_volume', 0) or total_data.get('volume', 0)
                
                if total_vol == 0 and 'recognition' in recognition_results:
                    print("1. 发现工程量计算异常，建议重新处理")
                    print("2. 可能需要修复识别结果到工程量计算的数据传递")
                elif total_vol > 0:
                    print("1. 工程量计算正常")
                    print("2. 可以进一步验证各构件类型的合理性")
                else:
                    print("1. 需要检查识别和计算流程")
            else:
                print("1. 缺少工程量计算结果，需要重新处理")
        else:
            print("1. 缺少识别结果，需要重新处理整个图纸")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_drawing_46_quantity() 