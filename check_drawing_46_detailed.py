#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查图纸46的识别结果
"""

import psycopg2
import json

def check_drawing_46_detailed():
    """详细检查图纸46的识别结果"""
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
        
        # 获取图纸46的数据
        cursor.execute('SELECT recognition_results FROM drawings WHERE id = 46')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸46")
            return
        
        print("=== 图纸46详细数据检查 ===")
        
        recognition_results = row[0]
        if recognition_results:
            print(f"数据类型: {type(recognition_results)}")
            print(f"主要键: {list(recognition_results.keys())}")
            print()
            
            # 检查recognition部分
            if 'recognition' in recognition_results:
                recognition = recognition_results['recognition']
                print("🔍 识别结果详情:")
                print(f"recognition类型: {type(recognition)}")
                
                if isinstance(recognition, dict):
                    print(f"recognition键: {list(recognition.keys())}")
                    for key, value in recognition.items():
                        print(f"  {key}: {type(value)} - {value}")
                elif isinstance(recognition, str):
                    print(f"recognition内容: {recognition}")
                else:
                    print(f"recognition值: {recognition}")
            
            # 检查quantities部分
            if 'quantities' in recognition_results:
                quantities = recognition_results['quantities']
                print(f"\n📊 工程量结果详情:")
                print(f"quantities类型: {type(quantities)}")
                
                if isinstance(quantities, dict):
                    for key, value in quantities.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"quantities值: {quantities}")
            
            # 输出完整的JSON结构（格式化）
            print(f"\n📄 完整数据结构:")
            print(json.dumps(recognition_results, ensure_ascii=False, indent=2))
        
        else:
            print("识别结果为空")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_drawing_46_detailed() 