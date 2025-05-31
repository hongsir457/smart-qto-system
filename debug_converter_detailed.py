#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试转换器问题
"""

import psycopg2
import json
import sys
import os

def debug_converter_detailed():
    """详细调试转换器问题"""
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
        
        print(f"=== 详细调试图纸47: {row[1]} ===")
        
        if row[2]:
            results = row[2]
            print(f"\n顶层结果类型: {type(results)}")
            print(f"顶层结果键: {list(results.keys())}")
            
            # 检查recognition部分
            if 'recognition' in results:
                recognition = results['recognition']
                print(f"\nrecognition类型: {type(recognition)}")
                print(f"recognition键: {list(recognition.keys())}")
                
                # 检查components
                if 'components' in recognition:
                    components = recognition['components']
                    print(f"\ncomponents类型: {type(components)}")
                    print(f"components键: {list(components.keys())}")
                    
                    # 详细检查每个组件类型
                    for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                        if component_type in components:
                            items = components[component_type]
                            print(f"\n=== {component_type.upper()} ===")
                            print(f"数量: {len(items)}")
                            
                            if items:
                                first_item = items[0]
                                print(f"第一个项目类型: {type(first_item)}")
                                print(f"第一个项目键: {list(first_item.keys())}")
                                print(f"第一个项目内容: {first_item}")
                                
                                # 检查是否有我们需要的字段
                                required_fields = ['bbox', 'confidence', 'dimensions']
                                missing_fields = []
                                for field in required_fields:
                                    if field not in first_item:
                                        missing_fields.append(field)
                                
                                if missing_fields:
                                    print(f"缺少字段: {missing_fields}")
                                else:
                                    print("包含所有必需字段")
                                    
                                    # 检查dimensions字段
                                    if 'dimensions' in first_item:
                                        dims = first_item['dimensions']
                                        print(f"dimensions: {dims}")
                                        print(f"dimensions类型: {type(dims)}")
                                        if isinstance(dims, dict):
                                            print(f"dimensions键: {list(dims.keys())}")
                
                # 检查是否有直接的组件数据
                for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                    if component_type in recognition:
                        items = recognition[component_type]
                        print(f"\n=== 直接的{component_type.upper()} ===")
                        print(f"数量: {len(items)}")
                        if items:
                            first_item = items[0]
                            print(f"第一个项目: {first_item}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_converter_detailed() 