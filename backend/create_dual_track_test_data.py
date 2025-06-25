#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建包含双轨协同分析两个输出点数据的测试图纸
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from app.database import SessionLocal
from app.models.drawing import Drawing
from app.models.user import User

def create_dual_track_test_data():
    """创建包含双轨协同分析两个输出点数据的测试图纸"""
    
    print("🔧 创建双轨协同分析测试数据")
    print("="*60)
    
    # 输出点1: OCR识别块数据
    ocr_recognition_display = {
        "drawing_basic_info": {
            "drawing_title": "二层柱结构配筋图",
            "drawing_number": "S-02", 
            "scale": "1:100",
            "project_name": "某住宅小区A栋",
            "drawing_type": "结构施工图",
            "design_unit": "某设计院",
            "approval_date": "2024-05-15"
        },
        "component_overview": {
            "component_ids": ["KZ1", "KZ2", "KZ3", "KZ4", "KL1", "KL2"],
            "component_types": ["框架柱", "框架梁"],
            "material_grades": ["C30", "HRB400"],
            "axis_lines": ["A", "B", "C", "1", "2", "3"],
            "summary": {
                "total_components": 6,
                "main_structure_type": "钢筋混凝土框架结构",
                "complexity_level": "中等"
            }
        },
        "ocr_source_info": {
            "total_slices": 8,
            "ocr_text_count": 156,
            "analysis_method": "基于切片OCR汇总的GPT分析",
            "processing_time": 12.5,
            "confidence_average": 0.89
        }
    }
    
    # 输出点2: 工程量清单块数据
    quantity_list_display = {
        "success": True,
        "components": [
            {
                "id": "KZ1",
                "component_type": "框架柱",
                "dimensions": "400×400",
                "material": "C30",
                "length": 3.6,
                "width": 0.4,
                "height": 0.4,
                "quantity": 4,
                "unit": "根",
                "volume": 2.304,
                "area": 5.76,
                "rebar_weight": 85.2
            },
            {
                "id": "KZ2", 
                "component_type": "框架柱",
                "dimensions": "500×500",
                "material": "C30",
                "length": 3.6,
                "width": 0.5,
                "height": 0.5,
                "quantity": 2,
                "unit": "根",
                "volume": 1.8,
                "area": 7.2,
                "rebar_weight": 96.5
            },
            {
                "id": "KL1",
                "component_type": "框架梁",
                "dimensions": "300×600",
                "material": "C30",
                "length": 6.0,
                "width": 0.3,
                "height": 0.6,
                "quantity": 3,
                "unit": "根",
                "volume": 3.24,
                "area": 10.8,
                "rebar_weight": 145.8
            }
        ],
        "summary": {
            "total_components": 9,
            "total_concrete_volume": 7.344,
            "total_rebar_weight": 327.5,
            "total_formwork_area": 23.76
        },
        "table_columns": [
            {"title": "构件编号", "dataIndex": "id", "key": "id"},
            {"title": "构件类型", "dataIndex": "component_type", "key": "component_type"},
            {"title": "尺寸规格", "dataIndex": "dimensions", "key": "dimensions"},
            {"title": "材料", "dataIndex": "material", "key": "material"},
            {"title": "数量", "dataIndex": "quantity", "key": "quantity"},
            {"title": "单位", "dataIndex": "unit", "key": "unit"},
            {"title": "体积(m³)", "dataIndex": "volume", "key": "volume"},
            {"title": "钢筋重量(kg)", "dataIndex": "rebar_weight", "key": "rebar_weight"}
        ]
    }
    
    # 构建完整的recognition_results数据
    recognition_results = {
        "ocr_recognition_display": ocr_recognition_display,
        "quantity_list_display": quantity_list_display,
        "analysis_metadata": {
            "analysis_method": "dual_track_analysis",
            "analysis_timestamp": datetime.now().isoformat(),
            "model_used": "GPT-4o",
            "processing_time": 45.8,
            "success": True
        }
    }
    
    # 构建processing_result数据（包含完整的双轨协同分析结果）
    processing_result = {
        "status": "success",
        "pipeline_type": "Dual-Track Analysis",
        "processing_summary": {
            "ocr_success": True,
            "vision_success": True,
            "components_count": 9,
            "merged_results": {
                "ocr_full_generated": True,
                "vision_full_generated": True
            }
        },
        "vision_scan_result": {
            "success": True,
            "analysis_method": "dual_track_analysis",
            "qto_data": {
                "components": quantity_list_display["components"],
                "drawing_info": ocr_recognition_display["drawing_basic_info"],
                "quantity_summary": quantity_list_display["summary"],
                "ocr_recognition_display": ocr_recognition_display,
                "quantity_list_display": quantity_list_display,
                "analysis_metadata": {
                    "analysis_method": "dual_track_analysis",
                    "steps_completed": ["dual_track_ocr", "dual_track_vision", "coordinate_restoration", "result_merge"],
                    "analysis_timestamp": datetime.now().isoformat(),
                    "model_used": "GPT-4o"
                }
            }
        },
        "ocr_result": {
            "success": True,
            "analysis_method": "enhanced_ocr",
            "statistics": ocr_recognition_display["ocr_source_info"]
        },
        "quantity_result": {
            "status": "success",
            "summary": quantity_list_display["summary"]
        }
    }
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 创建或获取测试用户
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                email="test@example.com",
                username="testuser",
                hashed_password="test_password_hash"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
        
        # 检查是否已存在ID为3的图纸
        existing_drawing = db.query(Drawing).filter(Drawing.id == 3).first()
        if existing_drawing:
            # 更新现有图纸
            existing_drawing.filename = "二层柱结构配筋图.pdf"
            existing_drawing.status = "completed"
            existing_drawing.components_count = 9
            existing_drawing.recognition_results = json.dumps(recognition_results, ensure_ascii=False)
            existing_drawing.processing_result = json.dumps(processing_result, ensure_ascii=False)
            existing_drawing.updated_at = datetime.now()
            existing_drawing.user_id = test_user.id
            
            db.commit()
            print(f"✅ 更新现有图纸ID 3:")
            print(f"   文件名: {existing_drawing.filename}")
            print(f"   状态: {existing_drawing.status}")
            print(f"   构件数量: {existing_drawing.components_count}")
            
            return 3
        else:
            # 创建新的图纸，指定ID为3
            test_drawing = Drawing(
                id=3,
                filename="二层柱结构配筋图.pdf",
                file_path="/uploads/dual_track_test.pdf",
                s3_key="drawings/dual_track_test.pdf",
                status="completed",
                file_size=1024000,
                file_type="application/pdf",
                components_count=9,
                recognition_results=json.dumps(recognition_results, ensure_ascii=False),
                processing_result=json.dumps(processing_result, ensure_ascii=False),
                user_id=test_user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.add(test_drawing)
            db.commit()
            db.refresh(test_drawing)
            
            print(f"✅ 成功创建双轨协同测试图纸:")
            print(f"   ID: {test_drawing.id}")
            print(f"   文件名: {test_drawing.filename}")
            print(f"   状态: {test_drawing.status}")
            print(f"   构件数量: {test_drawing.components_count}")
            
            return test_drawing.id
        
    except Exception as e:
        print(f"❌ 创建测试数据失败: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def verify_test_data(drawing_id: int):
    """验证测试数据"""
    
    print(f"\n🔍 验证图纸ID {drawing_id}的数据:")
    print("="*60)
    
    db = SessionLocal()
    try:
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            print(f"❌ 图纸ID {drawing_id}不存在")
            return
        
        # 检查recognition_results
        if drawing.recognition_results:
            recog = json.loads(drawing.recognition_results)
            print(f"📋 recognition_results检查:")
            print(f"   包含OCR识别块: {'ocr_recognition_display' in recog}")
            print(f"   包含工程量清单块: {'quantity_list_display' in recog}")
            
            if 'ocr_recognition_display' in recog:
                ocr_display = recog['ocr_recognition_display']
                print(f"   图纸标题: {ocr_display.get('drawing_basic_info', {}).get('drawing_title', 'N/A')}")
                print(f"   构件总数: {ocr_display.get('component_overview', {}).get('summary', {}).get('total_components', 0)}")
            
            if 'quantity_list_display' in recog:
                qty_display = recog['quantity_list_display']
                print(f"   工程量构件数: {len(qty_display.get('components', []))}")
                print(f"   混凝土体积: {qty_display.get('summary', {}).get('total_concrete_volume', 0)} m³")
        
        print(f"\n✅ 数据验证完成")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    drawing_id = create_dual_track_test_data()
    if drawing_id:
        verify_test_data(drawing_id)
        print(f"\n🎉 双轨协同分析测试数据创建成功！")
        print(f"💡 现在可以访问 http://localhost:3000/drawings/{drawing_id} 查看效果")
    else:
        print(f"\n❌ 测试数据创建失败") 