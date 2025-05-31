#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图纸47的工程量计算
"""

import psycopg2
import json
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.recognition_to_quantity_converter import RecognitionToQuantityConverter
from backend.app.services.quantity import QuantityCalculator

def test_drawing_47_quantity():
    """测试图纸47的工程量计算"""
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
        cursor.execute('SELECT id, filename, status, recognition_results FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print(f"图纸ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"状态: {row[2]}")
        
        if row[3]:
            recognition_results = row[3]
            
            print("\n=== 原始识别结果统计 ===")
            for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                if component_type in recognition_results:
                    count = len(recognition_results[component_type])
                    print(f"{component_type}: {count}个")
            
            # 使用转换器转换识别结果
            print("\n=== 开始转换识别结果 ===")
            converter = RecognitionToQuantityConverter()
            converted_results = converter.convert_recognition_results(recognition_results)
            
            print("\n=== 转换后结果统计 ===")
            for component_type, components in converted_results.items():
                if components:
                    print(f"{component_type}: {len(components)}个")
                    # 显示前3个构件的详细信息
                    for i, comp in enumerate(components[:3]):
                        print(f"  {comp['id']}: {comp['type']}")
                        if 'length' in comp:
                            length = comp.get('length', 0)
                            width = comp.get('width', comp.get('thickness', 0))
                            height = comp.get('height', comp.get('thickness', 0))
                            print(f"    尺寸: {length:.2f}m × {width:.2f}m × {height:.2f}m")
                        print(f"    置信度: {comp['confidence']:.2f}")
                    if len(components) > 3:
                        print(f"    ... 还有 {len(components) - 3} 个")
            
            # 计算工程量
            print("\n=== 开始计算工程量 ===")
            quantities = QuantityCalculator.process_recognition_results(converted_results)
            
            print("\n=== 工程量计算结果 ===")
            print(f"墙体工程量: {len(quantities['walls'])}项")
            print(f"柱子工程量: {len(quantities['columns'])}项")
            print(f"梁工程量: {len(quantities['beams'])}项")
            print(f"板工程量: {len(quantities['slabs'])}项")
            print(f"基础工程量: {len(quantities['foundations'])}项")
            
            # 显示总量统计
            total = quantities.get('total', {})
            print(f"\n=== 总量统计 ===")
            print(f"墙体总体积: {total.get('wall_volume', 0):.3f} m³")
            print(f"柱子总体积: {total.get('column_volume', 0):.3f} m³")
            print(f"梁总体积: {total.get('beam_volume', 0):.3f} m³")
            print(f"板总体积: {total.get('slab_volume', 0):.3f} m³")
            print(f"基础总体积: {total.get('foundation_volume', 0):.3f} m³")
            print(f"总体积: {total.get('total_volume', 0):.3f} m³")
            
            # 更新数据库中的工程量结果
            print("\n=== 更新数据库 ===")
            updated_results = {
                "recognition": recognition_results,
                "converted": converted_results,
                "quantities": quantities
            }
            
            cursor.execute(
                'UPDATE drawings SET recognition_results = %s WHERE id = %s',
                (json.dumps(updated_results), 47)
            )
            conn.commit()
            print("数据库更新完成")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_drawing_47_quantity() 