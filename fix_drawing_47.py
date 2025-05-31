#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复图纸47的数据结构并重新计算工程量
"""

import psycopg2
import json
import sys
import os

# 添加backend路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.recognition_to_quantity_converter import RecognitionToQuantityConverter
from backend.app.services.quantity import QuantityCalculator

def fix_drawing_47():
    """修复图纸47的数据结构并重新计算工程量"""
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
        
        print(f"=== 修复图纸47: {row[1]} ===")
        
        if row[2]:
            results = row[2]
            
            # 找到真正的识别结果
            original_recognition = None
            
            # 检查嵌套结构
            if 'recognition' in results:
                if 'recognition' in results['recognition']:
                    # 双重嵌套
                    nested_recognition = results['recognition']['recognition']
                    if 'components' in nested_recognition:
                        original_recognition = nested_recognition['components']
                        print("找到双重嵌套的识别结果")
                elif 'components' in results['recognition']:
                    # 单层嵌套
                    original_recognition = results['recognition']['components']
                    print("找到单层嵌套的识别结果")
                else:
                    # 直接在recognition中
                    original_recognition = results['recognition']
                    print("找到直接的识别结果")
            
            if original_recognition:
                print(f"\n🔍 原始识别结果统计:")
                total_components = 0
                for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                    if component_type in original_recognition:
                        count = len(original_recognition[component_type])
                        total_components += count
                        print(f"  {component_type}: {count}个")
                        
                        # 显示第一个组件的详细信息
                        if count > 0:
                            first_comp = original_recognition[component_type][0]
                            print(f"    示例: {first_comp}")
                
                print(f"  总构件数: {total_components}个")
                
                # 使用转换器转换识别结果
                print("\n🔄 开始转换识别结果:")
                converter = RecognitionToQuantityConverter()
                converted_results = converter.convert_recognition_results(original_recognition)
                
                print("\n转换后结果统计:")
                total_converted = 0
                for component_type, components in converted_results.items():
                    if components:
                        count = len(components)
                        total_converted += count
                        print(f"  {component_type}: {count}个")
                        
                        # 显示前2个组件的详细信息
                        for i, comp in enumerate(components[:2]):
                            print(f"    {i+1}. {comp.get('id', 'N/A')}: {comp.get('type', 'N/A')}")
                            if 'length' in comp:
                                length = comp.get('length', 0)
                                width = comp.get('width', comp.get('thickness', 0))
                                height = comp.get('height', comp.get('thickness', 0))
                                print(f"       尺寸: {length:.2f}m × {width:.2f}m × {height:.2f}m")
                            print(f"       置信度: {comp.get('confidence', 0):.2f}")
                        
                        if count > 2:
                            print(f"    ... 还有 {count - 2} 个")
                
                print(f"  转换后总构件数: {total_converted}个")
                
                # 计算工程量
                if total_converted > 0:
                    print("\n📊 开始计算工程量:")
                    quantities = QuantityCalculator.process_recognition_results(converted_results)
                    
                    print("\n工程量计算结果:")
                    for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                        if component_type in quantities:
                            items = quantities[component_type]
                            if isinstance(items, list) and items:
                                print(f"  {component_type}: {len(items)}项")
                    
                    # 显示总量统计
                    if 'total' in quantities:
                        total = quantities['total']
                        print(f"\n📈 总量统计:")
                        
                        volume_items = [
                            ('墙体总体积', 'wall_volume'),
                            ('柱子总体积', 'column_volume'),
                            ('梁总体积', 'beam_volume'),
                            ('板总体积', 'slab_volume'),
                            ('基础总体积', 'foundation_volume'),
                            ('总体积', 'total_volume')
                        ]
                        
                        for name, key in volume_items:
                            if key in total and total[key] > 0:
                                print(f"  {name}: {total[key]:.3f} m³")
                    
                    # 更新数据库
                    print("\n💾 更新数据库:")
                    updated_results = {
                        "recognition": original_recognition,
                        "converted": converted_results,
                        "quantities": quantities
                    }
                    
                    cursor.execute(
                        'UPDATE drawings SET recognition_results = %s WHERE id = %s',
                        (json.dumps(updated_results), 47)
                    )
                    conn.commit()
                    print("数据库更新完成")
                else:
                    print("转换后没有有效构件，跳过工程量计算")
            else:
                print("未找到有效的识别结果")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_drawing_47() 