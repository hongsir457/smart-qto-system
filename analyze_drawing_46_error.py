#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析图纸46的错误情况
"""

import psycopg2
import json
import requests
import os
from datetime import datetime

def analyze_drawing_46_error():
    """分析图纸46的错误情况"""
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
        
        # 获取图纸46的详细信息
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
        print("图纸46错误分析报告")
        print("=" * 80)
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"图纸ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"文件路径: {row[2]}")
        print(f"创建时间: {row[5]}")
        print(f"更新时间: {row[6]}")
        print(f"处理状态: {row[7]}")
        print()
        
        # 分析错误信息
        recognition_results = row[3]
        if recognition_results:
            print("🚨 错误信息分析:")
            print("-" * 50)
            
            if 'error' in recognition_results:
                error_msg = recognition_results['error']
                print(f"错误信息: {error_msg}")
                
                # 分析错误类型
                if 'CAD文件处理失败' in error_msg:
                    print("\n错误类型: CAD文件处理失败")
                    
                    if 'is not a DXF file' in error_msg:
                        print("具体问题: DWG文件无法直接读取")
                        print("原因分析:")
                        print("  1. DWG是AutoCAD的专有格式，需要特殊处理")
                        print("  2. 当前系统可能只支持DXF格式")
                        print("  3. 需要DWG到DXF的转换工具")
                        
                        print("\n解决方案:")
                        print("  1. 使用ezdxf库处理DXF文件")
                        print("  2. 使用ODA File Converter转换DWG到DXF")
                        print("  3. 使用FreeCAD或LibreCAD转换格式")
                        print("  4. 集成AutoCAD API或其他CAD处理库")
                
                # 检查文件下载情况
                if 'File' in error_msg and 'AppData\\Local\\Temp' in error_msg:
                    print("\n文件下载状态:")
                    temp_file_path = error_msg.split("'")[1] if "'" in error_msg else None
                    if temp_file_path:
                        print(f"临时文件路径: {temp_file_path}")
                        if os.path.exists(temp_file_path):
                            file_size = os.path.getsize(temp_file_path)
                            print(f"文件已下载，大小: {file_size} 字节")
                        else:
                            print("临时文件不存在")
            
            # 检查是否有其他识别结果
            print(f"\n识别结果键: {list(recognition_results.keys())}")
            
            if 'quantities' in recognition_results:
                quantities = recognition_results['quantities']
                print(f"工程量结果: {quantities}")
        
        # 检查文件访问情况
        file_url = row[2]
        if file_url:
            print(f"\n🌐 文件访问测试:")
            print("-" * 50)
            print(f"文件URL: {file_url}")
            
            try:
                # 测试文件下载
                response = requests.head(file_url, timeout=10)
                print(f"HTTP状态码: {response.status_code}")
                print(f"Content-Type: {response.headers.get('Content-Type', '未知')}")
                print(f"Content-Length: {response.headers.get('Content-Length', '未知')}")
                
                if response.status_code == 200:
                    print("✅ 文件可以正常访问")
                else:
                    print("⚠️ 文件访问异常")
                    
            except Exception as e:
                print(f"❌ 文件访问失败: {e}")
        
        # 文件类型分析
        filename = row[1]
        print(f"\n📁 文件类型分析:")
        print("-" * 50)
        print(f"文件名: {filename}")
        
        if filename.lower().endswith('.dwg'):
            print("文件类型: AutoCAD DWG")
            print("特征:")
            print("  - AutoCAD的原生二进制格式")
            print("  - 需要专门的库或工具读取")
            print("  - 通常比DXF文件更小，但兼容性较差")
            
            print("\n支持的处理方式:")
            print("  1. 转换为DXF: 使用ODA File Converter")
            print("  2. 直接读取: 使用AutoCAD COM接口")
            print("  3. 第三方库: 如Open Design Alliance SDK")
            print("  4. 在线转换: 使用在线DWG转DXF服务")
        
        elif filename.lower().endswith('.dxf'):
            print("文件类型: AutoCAD DXF")
            print("特征:")
            print("  - 基于ASCII或二进制的交换格式")
            print("  - 可以使用ezdxf等开源库读取")
            print("  - 兼容性更好")
        
        # 推荐处理方案
        print(f"\n💡 推荐处理方案:")
        print("-" * 50)
        
        if filename.lower().endswith('.dwg'):
            print("针对DWG文件的处理方案:")
            print("1. 【推荐】集成格式转换功能:")
            print("   - 安装ODA File Converter")
            print("   - 在处理前自动将DWG转换为DXF")
            print("   - 然后使用现有的DXF处理流程")
            
            print("\n2. 升级CAD处理模块:")
            print("   - 集成支持DWG的库（如dwg2dxf）")
            print("   - 修改recognition服务支持DWG直接处理")
            
            print("\n3. 预处理方案:")
            print("   - 要求用户上传DXF格式")
            print("   - 或提供在线格式转换功能")
        
        # 检查系统中其他CAD文件的处理情况
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors
            FROM drawings 
            WHERE filename LIKE '%.dwg' OR filename LIKE '%.dxf'
        ''')
        cad_stats = cursor.fetchone()
        
        if cad_stats:
            print(f"\n📊 系统CAD文件处理统计:")
            print("-" * 50)
            print(f"总CAD文件数: {cad_stats[0]}")
            print(f"处理成功数: {cad_stats[1]}")
            print(f"处理失败数: {cad_stats[2]}")
            
            if cad_stats[2] > 0:
                success_rate = (cad_stats[1] / cad_stats[0]) * 100 if cad_stats[0] > 0 else 0
                print(f"成功率: {success_rate:.1f}%")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_drawing_46_error() 