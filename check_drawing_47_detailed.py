#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查图纸47的数据
"""

import psycopg2
import json

def check_drawing_47_detailed():
    """详细检查图纸47的数据"""
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
        
        # 获取图纸47的所有信息
        cursor.execute('''
            SELECT id, filename, file_path, file_type, status, error_message, 
                   recognition_results, ocr_results, task_id, created_at, updated_at
            FROM drawings WHERE id = 47
        ''')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print("=== 图纸47详细信息 ===")
        print(f"ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"文件路径: {row[2]}")
        print(f"文件类型: {row[3]}")
        print(f"状态: {row[4]}")
        print(f"错误信息: {row[5]}")
        print(f"任务ID: {row[8]}")
        print(f"创建时间: {row[9]}")
        print(f"更新时间: {row[10]}")
        
        # 检查识别结果
        print("\n=== 识别结果 ===")
        if row[6]:
            recognition_results = row[6]
            print(f"识别结果类型: {type(recognition_results)}")
            
            if isinstance(recognition_results, dict):
                print("识别结果字段:")
                for key, value in recognition_results.items():
                    if isinstance(value, (list, dict)):
                        print(f"  {key}: {type(value)} (长度: {len(value) if hasattr(value, '__len__') else 'N/A'})")
                    else:
                        print(f"  {key}: {value}")
                
                # 详细检查每个组件类型
                for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                    if component_type in recognition_results:
                        components = recognition_results[component_type]
                        print(f"\n{component_type.upper()}:")
                        if isinstance(components, list) and components:
                            print(f"  数量: {len(components)}")
                            # 显示第一个组件的详细信息
                            first_comp = components[0]
                            print(f"  第一个组件: {first_comp}")
                        else:
                            print(f"  数据: {components}")
            else:
                print(f"识别结果内容: {recognition_results}")
        else:
            print("识别结果为空")
        
        # 检查OCR结果
        print("\n=== OCR结果 ===")
        if row[7]:
            ocr_results = row[7]
            print(f"OCR结果类型: {type(ocr_results)}")
            if isinstance(ocr_results, dict):
                print("OCR结果字段:")
                for key, value in ocr_results.items():
                    if isinstance(value, (list, dict)):
                        print(f"  {key}: {type(value)} (长度: {len(value) if hasattr(value, '__len__') else 'N/A'})")
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"OCR结果内容: {str(ocr_results)[:200]}...")
        else:
            print("OCR结果为空")
        
        # 检查最近的几个图纸
        print("\n=== 最近的5个图纸 ===")
        cursor.execute('''
            SELECT id, filename, status, created_at 
            FROM drawings 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        recent_drawings = cursor.fetchall()
        
        for drawing in recent_drawings:
            print(f"ID: {drawing[0]}, 文件名: {drawing[1]}, 状态: {drawing[2]}, 创建时间: {drawing[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_drawing_47_detailed() 