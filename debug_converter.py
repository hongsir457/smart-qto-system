#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试转换器问题
"""

import psycopg2
import json
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.recognition_to_quantity_converter import RecognitionToQuantityConverter

def debug_converter():
    """调试转换器问题"""
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
        cursor.execute('SELECT id, filename, recognition_results FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print(f"=== 调试图纸47: {row[1]} ===")
        
        if row[2] and 'recognition' in row[2]:
            recognition_results = row[2]['recognition']
            
            print("\n🔍 原始识别结果结构:")
            print(f"类型: {type(recognition_results)}")
            print(f"键: {list(recognition_results.keys())}")
            
            if 'components' in recognition_results:
                components = recognition_results['components']
                print(f"\ncomponents类型: {type(components)}")
                print(f"components键: {list(components.keys())}")
                
                # 检查每个组件类型
                for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                    if component_type in components:
                        items = components[component_type]
                        print(f"\n{component_type}:")
                        print(f"  数量: {len(items)}")
                        if items:
                            first_item = items[0]
                            print(f"  第一个项目: {first_item}")
                            print(f"  第一个项目的键: {list(first_item.keys())}")
            
            # 测试转换器
            print("\n🔄 测试转换器:")
            converter = RecognitionToQuantityConverter()
            
            # 直接传入recognition_results
            print("尝试转换整个recognition_results...")
            try:
                converted1 = converter.convert_recognition_results(recognition_results)
                print(f"转换结果1: {converted1}")
            except Exception as e:
                print(f"转换失败1: {e}")
            
            # 传入components部分
            if 'components' in recognition_results:
                print("\n尝试转换components部分...")
                try:
                    converted2 = converter.convert_recognition_results(recognition_results['components'])
                    print(f"转换结果2: {converted2}")
                except Exception as e:
                    print(f"转换失败2: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_converter() 