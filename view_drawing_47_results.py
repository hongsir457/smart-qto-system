#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看图纸47的识别和计算结果
"""

import psycopg2
import json

def view_drawing_47_results():
    """查看图纸47的识别和计算结果"""
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
        
        print(f"=== 图纸47: {row[1]} ===")
        
        if row[2]:
            results = row[2]
            
            # 查看原始识别结果
            if 'recognition' in results:
                recognition = results['recognition']
                print("\n🔍 原始识别结果:")
                for key, value in recognition.items():
                    if isinstance(value, list):
                        print(f"  {key}: {len(value)}个")
                        if value:  # 如果有数据，显示第一个
                            print(f"    示例: {value[0]}")
                    else:
                        print(f"  {key}: {value}")
            
            # 查看转换后结果
            if 'converted' in results:
                converted = results['converted']
                print("\n🔄 转换后结果:")
                total_components = 0
                for component_type, components in converted.items():
                    if isinstance(components, list):
                        count = len(components)
                        total_components += count
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
                
                print(f"\n  总构件数: {total_components}个")
            
            # 查看工程量计算结果
            if 'quantities' in results:
                quantities = results['quantities']
                print("\n📊 工程量计算结果:")
                
                # 显示各类构件的工程量
                for component_type in ['walls', 'columns', 'beams', 'slabs', 'foundations']:
                    if component_type in quantities:
                        items = quantities[component_type]
                        if isinstance(items, list) and items:
                            print(f"  {component_type}: {len(items)}项")
                            
                            # 显示前2项的详细信息
                            for i, item in enumerate(items[:2]):
                                print(f"    {i+1}. {item.get('id', 'N/A')}")
                                if 'volume' in item:
                                    print(f"       体积: {item['volume']:.3f} m³")
                                if 'area' in item:
                                    print(f"       面积: {item['area']:.3f} m²")
                                if 'length' in item:
                                    print(f"       长度: {item['length']:.3f} m")
                                if 'material' in item:
                                    print(f"       材料: {item['material']}")
                            
                            if len(items) > 2:
                                print(f"    ... 还有 {len(items) - 2} 项")
                
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
                        if key in total:
                            value = total[key]
                            if value > 0:
                                print(f"  {name}: {value:.3f} m³")
                    
                    # 显示其他统计信息
                    other_items = [
                        ('总面积', 'total_area', 'm²'),
                        ('总长度', 'total_length', 'm'),
                        ('总重量', 'total_weight', 'kg')
                    ]
                    
                    for name, key, unit in other_items:
                        if key in total and total[key] > 0:
                            print(f"  {name}: {total[key]:.3f} {unit}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    view_drawing_47_results() 