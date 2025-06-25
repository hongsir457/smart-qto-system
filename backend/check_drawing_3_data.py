#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查图纸ID 3的数据结构
"""

import sys
import json
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.models.drawing import Drawing

def check_drawing_3():
    """检查图纸ID 3的数据"""
    
    print("🔍 检查图纸ID 3的数据结构")
    print("="*60)
    
    # 连接数据库
    engine = create_engine('sqlite:///smart_qto.db')
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 查询图纸
        drawing = db.query(Drawing).filter(Drawing.id == 3).first()
        
        if not drawing:
            print("❌ 图纸ID 3不存在")
            return
        
        print("📋 基本信息:")
        print(f"   ID: {drawing.id}")
        print(f"   文件名: {drawing.filename}")
        print(f"   状态: {drawing.status}")
        print(f"   构件数量: {drawing.components_count}")
        print(f"   创建时间: {drawing.created_at}")
        print(f"   更新时间: {drawing.updated_at}")
        
        # 检查 processing_result
        print(f"\n📊 processing_result:")
        if drawing.processing_result:
            try:
                if isinstance(drawing.processing_result, str):
                    result = json.loads(drawing.processing_result)
                else:
                    result = drawing.processing_result
                
                print(f"   类型: {type(result)}")
                if isinstance(result, dict):
                    print(f"   主要字段: {list(result.keys())}")
                    
                    # 检查双轨协同分析结果
                    if 'vision_scan_result' in result:
                        vision_result = result['vision_scan_result']
                        print(f"\n🤖 Vision分析结果:")
                        print(f"   成功: {vision_result.get('success', False)}")
                        print(f"   错误: {vision_result.get('error', 'None')}")
                        
                        if 'qto_data' in vision_result:
                            qto_data = vision_result['qto_data']
                            components = qto_data.get('components', [])
                            print(f"   构件数量: {len(components)}")
                            
                            # 检查是否有双轨协同输出点数据
                            if 'ocr_recognition_display' in qto_data:
                                print(f"   ✅ 包含OCR识别块数据")
                            else:
                                print(f"   ❌ 缺少OCR识别块数据")
                                
                            if 'quantity_list_display' in qto_data:
                                print(f"   ✅ 包含工程量清单块数据")
                            else:
                                print(f"   ❌ 缺少工程量清单块数据")
                    
                    if 'ocr_result' in result:
                        ocr_result = result['ocr_result']
                        print(f"\n📝 OCR分析结果:")
                        print(f"   成功: {ocr_result.get('success', False)}")
                        
                    # 检查处理摘要
                    if 'processing_summary' in result:
                        summary = result['processing_summary']
                        print(f"\n📈 处理摘要:")
                        print(f"   OCR成功: {summary.get('ocr_success', False)}")
                        print(f"   Vision成功: {summary.get('vision_success', False)}")
                        print(f"   构件数量: {summary.get('components_count', 0)}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
        else:
            print("   ❌ processing_result为空")
        
        # 检查 recognition_results
        print(f"\n🎯 recognition_results:")
        if drawing.recognition_results:
            try:
                if isinstance(drawing.recognition_results, str):
                    recog = json.loads(drawing.recognition_results)
                else:
                    recog = drawing.recognition_results
                
                print(f"   类型: {type(recog)}")
                if isinstance(recog, dict):
                    print(f"   字段: {list(recog.keys())}")
                    
                    # 检查双轨协同输出点
                    if 'ocr_recognition_display' in recog:
                        print(f"   ✅ 包含OCR识别显示数据")
                    if 'quantity_list_display' in recog:
                        print(f"   ✅ 包含工程量清单显示数据")
                        
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
        else:
            print("   ❌ recognition_results为空")
        
        # 检查 ocr_results
        print(f"\n📖 ocr_results:")
        if drawing.ocr_results:
            try:
                if isinstance(drawing.ocr_results, str):
                    ocr = json.loads(drawing.ocr_results)
                else:
                    ocr = drawing.ocr_results
                
                print(f"   类型: {type(ocr)}")
                if isinstance(ocr, dict):
                    print(f"   字段: {list(ocr.keys())}")
                        
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
        else:
            print("   ❌ ocr_results为空")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_drawing_3() 