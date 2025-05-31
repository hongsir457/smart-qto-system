#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成图纸47的完整工程量报告
"""

import psycopg2
import json
from datetime import datetime

def generate_quantity_report():
    """生成图纸47的完整工程量报告"""
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
        cursor.execute('SELECT id, filename, recognition_results, created_at FROM drawings WHERE id = 47')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        drawing_id, filename, results, created_at = row
        
        print("=" * 80)
        print("                    智能工程量计算系统")
        print("                      工程量计算报告")
        print("=" * 80)
        print()
        
        print(f"项目名称: 一层柱结构改造加固工程")
        print(f"图纸文件: {filename}")
        print(f"图纸编号: {drawing_id}")
        print(f"计算时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        print(f"图纸上传: {created_at.strftime('%Y年%m月%d日 %H:%M:%S')}")
        print()
        
        if results and 'quantities' in results:
            quantities = results['quantities']
            
            print("一、构件识别统计")
            print("-" * 50)
            
            component_names = {
                'walls': '墙体',
                'columns': '柱子', 
                'beams': '梁',
                'slabs': '板',
                'foundations': '基础'
            }
            
            total_items = 0
            for component_type, chinese_name in component_names.items():
                if component_type in quantities:
                    items = quantities[component_type]
                    count = len(items) if isinstance(items, list) else 0
                    total_items += count
                    print(f"{chinese_name:8}: {count:4}个")
            
            print(f"{'总计':8}: {total_items:4}个")
            print()
            
            print("二、工程量计算结果")
            print("-" * 50)
            
            if 'total' in quantities:
                total = quantities['total']
                
                # 体积统计
                print("2.1 混凝土工程量")
                volume_items = [
                    ('墙体混凝土', 'wall_volume'),
                    ('柱混凝土', 'column_volume'),
                    ('梁混凝土', 'beam_volume'),
                    ('板混凝土', 'slab_volume'),
                    ('基础混凝土', 'foundation_volume')
                ]
                
                total_concrete = 0
                for name, key in volume_items:
                    if key in total:
                        volume = total[key]
                        total_concrete += volume
                        if volume > 0:
                            print(f"    {name:12}: {volume:8.3f} m³")
                
                print(f"    {'混凝土小计':12}: {total_concrete:8.3f} m³")
                print()
                
                # 详细构件清单
                print("三、详细构件清单")
                print("-" * 50)
                
                for component_type, chinese_name in component_names.items():
                    if component_type in quantities:
                        items = quantities[component_type]
                        if isinstance(items, list) and items:
                            print(f"\n3.{list(component_names.keys()).index(component_type) + 1} {chinese_name}清单")
                            print(f"{'编号':8} {'材料':12} {'体积(m³)':12} {'备注':20}")
                            print("-" * 60)
                            
                            subtotal_volume = 0
                            for i, item in enumerate(items[:10]):  # 只显示前10个
                                item_id = item.get('id', f'{component_type[0].upper()}{i+1:03d}')
                                material = item.get('material', 'C30混凝土')
                                volume = item.get('volume', 0)
                                subtotal_volume += volume
                                
                                print(f"{item_id:8} {material:12} {volume:12.3f}")
                            
                            if len(items) > 10:
                                remaining = len(items) - 10
                                print(f"{'...':8} {'...':12} {'...':12} (还有{remaining}项)")
                            
                            print(f"{'小计':8} {'':12} {subtotal_volume:12.3f}")
                
                print()
                print("四、工程量汇总")
                print("-" * 50)
                print(f"混凝土总量: {total_concrete:.3f} m³")
                
                # 估算其他工程量
                if total_concrete > 0:
                    # 按经验系数估算
                    formwork_area = total_concrete * 6.5  # 模板面积系数
                    rebar_weight = total_concrete * 80    # 钢筋重量系数(kg/m³)
                    
                    print(f"模板面积: {formwork_area:.2f} m²")
                    print(f"钢筋重量: {rebar_weight:.1f} kg")
                
                print()
                print("五、技术说明")
                print("-" * 50)
                print("1. 本报告基于AI智能识别技术自动生成")
                print("2. 混凝土强度等级按C30计算")
                print("3. 构件尺寸基于图纸识别结果")
                print("4. 模板和钢筋用量为估算值，实际用量需根据详细设计确定")
                print("5. 本报告仅供参考，最终工程量以施工图为准")
                
                print()
                print("六、系统信息")
                print("-" * 50)
                print("识别引擎: YOLOv8x + 传统检测算法")
                print("计算引擎: 智能工程量计算系统 v1.0")
                print("置信度阈值: 0.7")
                print("处理状态: 计算完成")
                
        print()
        print("=" * 80)
        print("                    报告结束")
        print("=" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_quantity_report() 