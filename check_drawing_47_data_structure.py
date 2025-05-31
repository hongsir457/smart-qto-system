#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查图纸47的数据结构
"""

import psycopg2
import json

def check_data_structure():
    """检查图纸47的数据结构"""
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
        
        # 获取图纸47的数据
        cursor.execute('SELECT recognition_results, ocr_results FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print("=== 图纸47数据结构检查 ===")
        
        # 检查识别结果
        recognition_results = row[0]
        print(f"\n📊 识别结果数据类型: {type(recognition_results)}")
        
        if recognition_results:
            print(f"识别结果键: {list(recognition_results.keys())}")
            
            for key, value in recognition_results.items():
                print(f"\n{key}:")
                print(f"  类型: {type(value)}")
                if isinstance(value, dict):
                    print(f"  键: {list(value.keys())}")
                    if key == 'recognition_results':
                        for sub_key, sub_value in value.items():
                            print(f"    {sub_key}: {sub_value}")
                    elif key == 'quantity_results':
                        for sub_key, sub_value in value.items():
                            print(f"    {sub_key}: {type(sub_value)}")
                            if isinstance(sub_value, dict) and 'total_volume' in sub_value:
                                print(f"      total_volume: {sub_value['total_volume']}")
                elif isinstance(value, list):
                    print(f"  长度: {len(value)}")
                else:
                    print(f"  值: {value}")
        
        # 检查OCR结果
        ocr_results = row[1]
        print(f"\n📝 OCR结果数据类型: {type(ocr_results)}")
        
        if ocr_results:
            print(f"OCR结果键: {list(ocr_results.keys())}")
            
            if 'text' in ocr_results:
                text_data = ocr_results['text']
                print(f"text数据类型: {type(text_data)}")
                if isinstance(text_data, dict):
                    print(f"text键: {list(text_data.keys())}")
                    if 'text' in text_data:
                        actual_text = text_data['text']
                        print(f"实际文本长度: {len(actual_text)}")
                        print(f"文本开头: {actual_text[:100]}...")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_data_structure() 