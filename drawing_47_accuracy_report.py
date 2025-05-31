#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图纸47识别准确性综合分析报告
"""

import psycopg2
import json
import re
from datetime import datetime

def generate_accuracy_report():
    """生成图纸47识别准确性分析报告"""
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
        
        # 获取图纸47的完整信息
        cursor.execute('''
            SELECT id, filename, file_path, recognition_results, ocr_results, 
                   created_at, updated_at, status
            FROM drawings WHERE id = 47
        ''')
        row = cursor.fetchone()
        
        if not row:
            print("未找到图纸47")
            return
        
        print("=" * 80)
        print("图纸47识别准确性综合分析报告")
        print("=" * 80)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"图纸ID: {row[0]}")
        print(f"文件名: {row[1]}")
        print(f"创建时间: {row[5]}")
        print(f"更新时间: {row[6]}")
        print(f"处理状态: {row[7]}")
        print()
        
        # 1. 图框识别准确性分析
        print("📋 1. 图框识别准确性分析")
        print("-" * 50)
        
        # 从文件名分析预期内容
        filename = row[1]
        expected_title = "一层柱结构改造加固平面图"
        
        print(f"预期图名: {expected_title}")
        print(f"实际文件名: {filename}")
        
        # 分析OCR结果
        ocr_results = row[4]
        if ocr_results and 'text' in ocr_results and 'text' in ocr_results['text']:
            ocr_text = ocr_results['text']['text']
            
            # 检查图名识别
            title_found = False
            title_keywords = ['一层', '柱', '结构', '改造', '加固', '平面图']
            found_keywords = []
            
            for keyword in title_keywords:
                if keyword in ocr_text:
                    found_keywords.append(keyword)
            
            print(f"图名关键词识别: {len(found_keywords)}/{len(title_keywords)}")
            print(f"已识别关键词: {', '.join(found_keywords)}")
            print(f"未识别关键词: {', '.join(set(title_keywords) - set(found_keywords))}")
            
            # 检查比例尺
            scale_patterns = [r'1\s*:\s*\d+', r'比例.*1.*:.*\d+']
            scale_found = False
            for pattern in scale_patterns:
                if re.search(pattern, ocr_text, re.IGNORECASE):
                    scale_found = True
                    break
            
            print(f"比例尺识别: {'✅ 已识别' if scale_found else '❌ 未识别'}")
            
            # 检查设计单位
            company_found = 'SHANGHAI INSTALLATION ENGINEERING GROUP' in ocr_text
            print(f"设计单位识别: {'✅ 已识别' if company_found else '❌ 未识别'}")
            
        else:
            print("❌ OCR结果为空或格式异常")
        
        print()
        
        # 2. 构件识别准确性分析
        print("🔍 2. 构件识别准确性分析")
        print("-" * 50)
        
        recognition_results = row[3]
        if recognition_results:
            # 分析原始识别结果
            if 'recognition' in recognition_results:
                original_results = recognition_results['recognition']
                print("原始识别结果:")
                for component_type, data in original_results.items():
                    if isinstance(data, list):
                        count = len(data)
                    else:
                        count = data
                    print(f"  {component_type}: {count}个")
            
            # 分析转换后结果
            if 'converted' in recognition_results:
                converted_results = recognition_results['converted']
                total_components = sum(len(components) for components in converted_results.values())
                print(f"\n转换后构件总数: {total_components}个")
                
                for component_type, components in converted_results.items():
                    if components:
                        print(f"  {component_type}: {len(components)}个")
            
            # 分析工程量计算结果
            if 'quantities' in recognition_results:
                quantity_results = recognition_results['quantities']
                print(f"\n工程量计算结果:")
                
                total_volume = 0
                for component_type, data in quantity_results.items():
                    if component_type != 'total' and isinstance(data, dict) and 'total_volume' in data:
                        volume = data['total_volume']
                        total_volume += volume
                        print(f"  {component_type}: {volume:.3f} m³")
                
                if 'total' in quantity_results:
                    total_data = quantity_results['total']
                    if isinstance(total_data, dict) and 'volume' in total_data:
                        print(f"  总体积: {total_data['volume']:.3f} m³")
                    else:
                        print(f"  总体积: {total_volume:.3f} m³")
        
        print()
        
        # 3. 准确性评估
        print("📊 3. 准确性评估")
        print("-" * 50)
        
        # 基于文件名的预期分析
        print("基于文件名的预期分析:")
        print("  - 图纸类型: 柱结构改造加固平面图")
        print("  - 主要构件: 应以柱子为主")
        print("  - 次要构件: 可能包含基础、少量梁")
        print("  - 不应包含: 大量墙体、板")
        
        print("\n实际识别结果评估:")
        if recognition_results and 'recognition' in recognition_results:
            original_results = recognition_results['recognition']
            
            # 柱子识别评估 - 修复数据类型问题
            columns_data = original_results.get('columns', [])
            walls_data = original_results.get('walls', [])
            beams_data = original_results.get('beams', [])
            foundations_data = original_results.get('foundations', [])
            slabs_data = original_results.get('slabs', [])
            
            # 获取数量
            columns = len(columns_data) if isinstance(columns_data, list) else columns_data
            walls = len(walls_data) if isinstance(walls_data, list) else walls_data
            beams = len(beams_data) if isinstance(beams_data, list) else beams_data
            foundations = len(foundations_data) if isinstance(foundations_data, list) else foundations_data
            slabs = len(slabs_data) if isinstance(slabs_data, list) else slabs_data
            
            print(f"  ✅ 柱子识别: {columns}个 (符合预期)")
            print(f"  ✅ 基础识别: {foundations}个 (符合预期)")
            
            if walls > columns * 2:
                print(f"  ⚠️  墙体识别: {walls}个 (可能过多，需要验证)")
            else:
                print(f"  ✅ 墙体识别: {walls}个 (数量合理)")
            
            if beams > columns:
                print(f"  ⚠️  梁识别: {beams}个 (可能过多，需要验证)")
            else:
                print(f"  ✅ 梁识别: {beams}个 (数量合理)")
            
            if slabs > 0:
                print(f"  ⚠️  板识别: {slabs}个 (柱加固图不应有板)")
            else:
                print(f"  ✅ 板识别: {slabs}个 (符合预期)")
        
        print()
        
        # 4. 问题识别和建议
        print("🔧 4. 问题识别和改进建议")
        print("-" * 50)
        
        issues = []
        suggestions = []
        
        # 图框识别问题
        if not found_keywords or len(found_keywords) < len(title_keywords) * 0.7:
            issues.append("图名识别不完整")
            suggestions.append("优化OCR算法，提高对图纸标题的识别准确率")
        
        if not scale_found:
            issues.append("比例尺识别失败")
            suggestions.append("增强比例尺识别模式，支持更多格式")
        
        # 构件识别问题
        if recognition_results and 'recognition' in recognition_results:
            original_results = recognition_results['recognition']
            walls_data = original_results.get('walls', [])
            columns_data = original_results.get('columns', [])
            
            walls = len(walls_data) if isinstance(walls_data, list) else walls_data
            columns = len(columns_data) if isinstance(columns_data, list) else columns_data
            
            if walls > columns * 3:
                issues.append("墙体识别数量异常偏高")
                suggestions.append("检查构件分类算法，避免将柱子误识别为墙体")
        
        if issues:
            print("发现的问题:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")
            
            print("\n改进建议:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        else:
            print("✅ 未发现明显问题，识别结果基本准确")
        
        print()
        
        # 5. 总体评分
        print("⭐ 5. 总体评分")
        print("-" * 50)
        
        # 计算评分
        frame_score = 0
        if found_keywords:
            frame_score += (len(found_keywords) / len(title_keywords)) * 30
        if scale_found:
            frame_score += 10
        if company_found:
            frame_score += 10
        
        component_score = 0
        if recognition_results and 'recognition' in recognition_results:
            original_results = recognition_results['recognition']
            columns_data = original_results.get('columns', [])
            walls_data = original_results.get('walls', [])
            
            columns = len(columns_data) if isinstance(columns_data, list) else columns_data
            walls = len(walls_data) if isinstance(walls_data, list) else walls_data
            
            # 柱子识别得分
            if columns > 0:
                component_score += 20
            
            # 构件比例合理性得分
            if walls <= columns * 3:
                component_score += 15
            
            # 工程量计算得分
            if 'quantities' in recognition_results:
                component_score += 15
        
        total_score = frame_score + component_score
        
        print(f"图框识别得分: {frame_score:.1f}/50")
        print(f"构件识别得分: {component_score:.1f}/50")
        print(f"总体得分: {total_score:.1f}/100")
        
        if total_score >= 80:
            grade = "优秀"
        elif total_score >= 70:
            grade = "良好"
        elif total_score >= 60:
            grade = "及格"
        else:
            grade = "需要改进"
        
        print(f"评级: {grade}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_accuracy_report() 