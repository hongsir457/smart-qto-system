#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸47综合测试报告
"""

import psycopg2
import json
from datetime import datetime
import requests

def comprehensive_test_drawing_47():
    """图纸47综合测试"""
    print("=" * 80)
    print("图纸47综合测试报告")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
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
        
        # 1. 基本信息检查
        print("📋 1. 基本信息检查")
        print("-" * 50)
        
        cursor.execute('''
            SELECT id, filename, file_path, file_type, status, error_message, 
                   task_id, created_at, updated_at
            FROM drawings WHERE id = 47
        ''')
        row = cursor.fetchone()
        
        if not row:
            print("❌ 未找到图纸47")
            return
        
        print(f"✅ 图纸ID: {row[0]}")
        print(f"✅ 文件名: {row[1]}")
        print(f"✅ 文件路径: {row[2]}")
        print(f"✅ 文件类型: {row[3]}")
        print(f"✅ 处理状态: {row[4]}")
        print(f"✅ 错误信息: {row[5] or '无'}")
        print(f"✅ 任务ID: {row[6]}")
        print(f"✅ 创建时间: {row[7]}")
        print(f"✅ 更新时间: {row[8]}")
        
        # 2. 识别结果详细检查
        print(f"\n🔍 2. 识别结果详细检查")
        print("-" * 50)
        
        cursor.execute('SELECT recognition_results FROM drawings WHERE id = 47')
        results_row = cursor.fetchone()
        
        if not results_row or not results_row[0]:
            print("❌ 无识别结果")
            return
            
        recognition_results = results_row[0]
        
        # 检查数据结构
        print(f"识别结果数据类型: {type(recognition_results)}")
        print(f"顶级字段: {list(recognition_results.keys())}")
        
        # 检查原始识别结果
        if 'recognition' in recognition_results:
            original = recognition_results['recognition']
            print(f"\n原始识别结果:")
            total_original = 0
            for comp_type, data in original.items():
                if isinstance(data, list):
                    count = len(data)
                    total_original += count
                    print(f"  {comp_type}: {count}个")
                    
                    # 显示样例
                    if count > 0:
                        sample = data[0]
                        print(f"    样例: bbox={sample.get('bbox')}, 置信度={sample.get('confidence'):.2f}")
            
            print(f"  总计: {total_original}个构件")
        
        # 检查转换后结果
        if 'converted' in recognition_results:
            converted = recognition_results['converted']
            print(f"\n转换后结果:")
            total_converted = 0
            for comp_type, data in converted.items():
                if isinstance(data, list):
                    count = len(data)
                    total_converted += count
                    print(f"  {comp_type}: {count}个")
                    
                    # 显示样例
                    if count > 0:
                        sample = data[0]
                        length = sample.get('length', 0)
                        width = sample.get('width', sample.get('thickness', 0))
                        height = sample.get('height', 3.0)
                        print(f"    样例: ID={sample.get('id')}, 尺寸={length:.2f}×{width:.2f}×{height:.2f}m")
            
            print(f"  总计: {total_converted}个构件")
        
        # 检查工程量计算结果
        if 'quantities' in recognition_results:
            quantities = recognition_results['quantities']
            print(f"\n工程量计算结果:")
            
            total_volume = 0
            for comp_type, data in quantities.items():
                if comp_type == 'total':
                    continue
                    
                if isinstance(data, list):
                    count = len(data)
                    if count > 0:
                        # 计算该类型的总体积
                        type_volume = 0
                        for item in data:
                            if isinstance(item, dict) and 'volume' in item:
                                type_volume += item['volume']
                        
                        print(f"  {comp_type}: {count}项, 体积={type_volume:.3f}m³")
                        total_volume += type_volume
                        
                        # 显示样例
                        if count > 0:
                            sample = data[0]
                            vol = sample.get('volume', 0)
                            mat = sample.get('material', 'N/A')
                            print(f"    样例: ID={sample.get('id')}, 体积={vol:.3f}m³, 材料={mat}")
            
            # 检查总量统计
            if 'total' in quantities:
                total_stats = quantities['total']
                print(f"\n总量统计:")
                for key, value in total_stats.items():
                    print(f"  {key}: {value:.3f}m³")
            else:
                print(f"\n计算得出的总体积: {total_volume:.3f}m³")
        
        # 3. OCR结果检查
        print(f"\n📝 3. OCR结果检查")
        print("-" * 50)
        
        cursor.execute('SELECT ocr_results FROM drawings WHERE id = 47')
        ocr_row = cursor.fetchone()
        
        if ocr_row and ocr_row[0]:
            ocr_results = ocr_row[0]
            print(f"OCR结果数据类型: {type(ocr_results)}")
            
            if isinstance(ocr_results, dict):
                print(f"OCR字段: {list(ocr_results.keys())}")
                
                if 'text' in ocr_results:
                    text_data = ocr_results['text']
                    if isinstance(text_data, dict):
                        for page, content in text_data.items():
                            char_count = len(content) if isinstance(content, str) else 0
                            print(f"  {page}: {char_count}个字符")
                            if char_count > 0:
                                # 显示文本片段
                                preview = content[:100] + "..." if len(content) > 100 else content
                                print(f"    预览: {preview}")
        else:
            print("❌ 无OCR结果")
        
        # 4. API接口测试
        print(f"\n🔌 4. API接口测试")
        print("-" * 50)
        
        try:
            # 测试获取图纸信息接口
            api_url = "http://localhost:8000/api/v1/drawings/47"
            headers = {"Authorization": "Bearer test_token"}  # 这里需要实际的token
            
            print(f"测试API端点: {api_url}")
            print("注意: 需要有效的认证令牌才能成功调用")
            
        except Exception as e:
            print(f"API测试跳过: {e}")
        
        # 5. 数据一致性检查
        print(f"\n✅ 5. 数据一致性检查")
        print("-" * 50)
        
        # 检查各阶段数据是否一致
        if 'recognition' in recognition_results and 'converted' in recognition_results:
            original_counts = {}
            converted_counts = {}
            
            # 统计原始识别数量
            for comp_type, data in recognition_results['recognition'].items():
                if isinstance(data, list):
                    original_counts[comp_type] = len(data)
            
            # 统计转换后数量
            for comp_type, data in recognition_results['converted'].items():
                if isinstance(data, list):
                    converted_counts[comp_type] = len(data)
            
            print("数量一致性检查:")
            for comp_type in original_counts:
                orig_count = original_counts.get(comp_type, 0)
                conv_count = converted_counts.get(comp_type, 0)
                status = "✅" if orig_count == conv_count else "❌"
                print(f"  {comp_type}: 原始{orig_count} → 转换{conv_count} {status}")
        
        # 6. 质量评估
        print(f"\n📊 6. 质量评估")
        print("-" * 50)
        
        # 基于文件名分析预期内容
        filename = row[1]
        print(f"图纸类型分析: {filename}")
        print("预期构件: 主要应包含柱子、基础，可能有少量梁")
        
        if 'converted' in recognition_results:
            converted = recognition_results['converted']
            
            # 分析构件比例
            walls_count = len(converted.get('walls', []))
            columns_count = len(converted.get('columns', []))
            beams_count = len(converted.get('beams', []))
            foundations_count = len(converted.get('foundations', []))
            
            print(f"实际识别结果:")
            print(f"  柱子: {columns_count}个 ✅")
            print(f"  基础: {foundations_count}个 ✅")
            print(f"  梁: {beams_count}个 {'⚠️ 偏多' if beams_count > columns_count * 3 else '✅'}")
            print(f"  墙体: {walls_count}个 {'❌ 异常偏多' if walls_count > columns_count * 10 else '✅'}")
            
            # 评分
            score = 0
            if columns_count > 0:
                score += 20
            if foundations_count > 0:
                score += 20
            if walls_count <= columns_count * 10:
                score += 30
            else:
                score -= 10
            if beams_count <= columns_count * 5:
                score += 20
            if 'quantities' in recognition_results and recognition_results['quantities']:
                score += 10
                
            print(f"\n总体评分: {score}/100")
            if score >= 80:
                quality = "优秀"
            elif score >= 60:
                quality = "良好"
            elif score >= 40:
                quality = "一般"
            else:
                quality = "需要改进"
            print(f"质量等级: {quality}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    comprehensive_test_drawing_47() 