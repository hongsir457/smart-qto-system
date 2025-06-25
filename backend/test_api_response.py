#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API返回的数据结构
"""

import sys
import json
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from app.database import SessionLocal
from app.models.drawing import Drawing

def test_api_response():
    """测试图纸ID 3的API响应数据结构"""
    
    print("🔍 测试图纸ID 3的API响应数据结构")
    print("="*60)
    
    # 使用正确的数据库连接
    db = SessionLocal()
    
    try:
        # 查询图纸
        drawing = db.query(Drawing).filter(Drawing.id == 3).first()
        
        if not drawing:
            print("❌ 图纸ID 3不存在")
            return
        
        # 模拟API响应数据
        api_response = {
            "id": drawing.id,
            "filename": drawing.filename,
            "status": drawing.status,
            "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
            "updated_at": drawing.updated_at.isoformat() if drawing.updated_at else None,
            "progress": 100,
            "file_size": drawing.file_size,
            "file_type": drawing.file_type,
            "file_path": drawing.file_path,
            "processing_result": drawing.processing_result,
            "error_message": drawing.error_message,
            "ocr_results": drawing.ocr_results,
            "recognition_results": drawing.recognition_results,
            "ocr_recognition_display": drawing.ocr_recognition_display,  # 新增独立字段
            "quantity_list_display": drawing.quantity_list_display,      # 新增独立字段
            "components_count": drawing.components_count or 0,
            "task_id": drawing.task_id
        }
        
        print("📋 模拟API响应数据结构:")
        print(f"   ID: {api_response['id']}")
        print(f"   文件名: {api_response['filename']}")
        print(f"   状态: {api_response['status']}")
        print(f"   构件数量: {api_response['components_count']}")
        
        # 检查独立字段
        print(f"\n🔧 独立字段检查:")
        print(f"   ocr_recognition_display: {'✅ 有数据' if api_response['ocr_recognition_display'] else '❌ 无数据'}")
        print(f"   quantity_list_display: {'✅ 有数据' if api_response['quantity_list_display'] else '❌ 无数据'}")
        
        # 检查独立字段内容
        if api_response['ocr_recognition_display']:
            ocr_data = api_response['ocr_recognition_display']
            print(f"\n✅ OCR识别块内容:")
            print(f"   图纸标题: {ocr_data.get('drawing_basic_info', {}).get('drawing_title', 'N/A')}")
            print(f"   构件总数: {ocr_data.get('component_overview', {}).get('summary', {}).get('total_components', 0)}")
            
        if api_response['quantity_list_display']:
            qty_data = api_response['quantity_list_display']
            print(f"\n✅ 工程量清单块内容:")
            print(f"   成功状态: {qty_data.get('success', False)}")
            print(f"   构件数量: {len(qty_data.get('components', []))}")
            print(f"   总体积: {qty_data.get('summary', {}).get('total_concrete_volume', 0)} m³")
        
        # 检查recognition_results结构（兼容性）
        if api_response['recognition_results']:
            try:
                if isinstance(api_response['recognition_results'], str):
                    recog_data = json.loads(api_response['recognition_results'])
                else:
                    recog_data = api_response['recognition_results']
                
                print(f"\n📊 recognition_results结构（兼容性）:")
                print(f"   类型: {type(recog_data)}")
                if isinstance(recog_data, dict):
                    print(f"   主要字段: {list(recog_data.keys())}")
                    
                    # 检查双轨协同输出点
                    if 'ocr_recognition_display' in recog_data:
                        ocr_display = recog_data['ocr_recognition_display']
                        print(f"\n✅ 嵌套OCR识别块数据:")
                        print(f"   图纸标题: {ocr_display.get('drawing_basic_info', {}).get('drawing_title', 'N/A')}")
                        print(f"   构件编号数: {len(ocr_display.get('component_overview', {}).get('component_ids', []))}")
                        print(f"   构件类型数: {len(ocr_display.get('component_overview', {}).get('component_types', []))}")
                    
                    if 'quantity_list_display' in recog_data:
                        qty_display = recog_data['quantity_list_display']
                        print(f"\n✅ 嵌套工程量清单块数据:")
                        print(f"   成功状态: {qty_display.get('success', False)}")
                        print(f"   构件数量: {len(qty_display.get('components', []))}")
                        print(f"   总体积: {qty_display.get('summary', {}).get('total_concrete_volume', 0)} m³")
                        print(f"   表格列数: {len(qty_display.get('table_columns', []))}")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
        else:
            print(f"\n❌ recognition_results为空")
        
        # 保存测试数据到文件
        with open("api_response_test.json", "w", encoding="utf-8") as f:
            # 序列化时处理datetime对象
            def json_serializer(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            json.dump(api_response, f, ensure_ascii=False, indent=2, default=json_serializer)
        
        print(f"\n💾 测试数据已保存到: api_response_test.json")
        
        # 验证前端期望的数据结构
        print(f"\n🔍 前端数据结构验证:")
        
        # 检查前端期望的字段
        frontend_checks = [
            ('id', api_response.get('id')),
            ('filename', api_response.get('filename')),
            ('status', api_response.get('status')),
            ('ocr_recognition_display', api_response.get('ocr_recognition_display')),
            ('quantity_list_display', api_response.get('quantity_list_display')),
            ('recognition_results', api_response.get('recognition_results')),
            ('components_count', api_response.get('components_count'))
        ]
        
        for field, value in frontend_checks:
            status = "✅" if value is not None else "❌"
            print(f"   {status} {field}: {value is not None}")
        
        print(f"\n🎉 API响应数据结构测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_api_response() 