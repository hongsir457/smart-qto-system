#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为图纸ID 4 创建双轨协同分析测试数据
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def create_drawing_4_data():
    """为图纸ID 4 创建双轨协同分析测试数据"""
    
    print("🔧 为图纸ID 4 创建双轨协同数据")
    print("="*60)
    
    try:
        from app.database import engine, SessionLocal
        from app.models.drawing import Drawing
        from app.models.user import User
        
        # 创建所有表
        print("📋 创建数据库表...")
        Drawing.metadata.create_all(bind=engine)
        User.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
        
        # 创建测试用户
        db = SessionLocal()
        try:
            # 检查是否已存在测试用户
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
                print("✅ 测试用户创建成功")
            else:
                print("✅ 测试用户已存在")
            
            # 输出点1: OCR识别块数据
            ocr_recognition_display = {
                "drawing_basic_info": {
                    "drawing_title": "三层框架结构平面图",
                    "drawing_number": "JG-03-01", 
                    "scale": "1:100",
                    "project_name": "某办公楼项目",
                    "drawing_type": "结构平面图",
                    "design_unit": "某建筑设计院",
                    "approval_date": "2024-06-20"
                },
                "component_overview": {
                    "component_ids": ["KZ1", "KZ2", "KZ3", "KZ4", "KZ5", "KZ6", "L1", "L2", "L3", "L4", "L5", "B1", "B2", "B3"],
                    "component_types": ["框架柱", "框架梁", "楼板"],
                    "material_grades": ["C30", "C25", "HRB400"],
                    "axis_lines": ["A", "B", "C", "D", "1", "2", "3", "4", "5"],
                    "summary": {
                        "total_components": 14,
                        "main_structure_type": "框架结构",
                        "complexity_level": "中等"
                    }
                },
                "ocr_source_info": {
                    "total_slices": 24,
                    "ocr_text_count": 156,
                    "analysis_method": "dual_track_ocr_analysis",
                    "processing_time": 18.7,
                    "confidence_average": 0.92
                }
            }
            
            # 输出点2: 工程量清单块数据
            quantity_list_display = {
                "success": True,
                "components": [
                    {
                        "key": "KZ1",
                        "component_id": "KZ1",
                        "component_type": "框架柱",
                        "dimensions": "400×400×3000",
                        "material": "C30",
                        "quantity": 1,
                        "unit": "根",
                        "volume": "0.48",
                        "area": "4.80",
                        "structural_role": "承重",
                        "connections": "L1, L2",
                        "location": "A1轴线交点",
                        "confidence": "95.2%",
                        "source_slice": "slice_2_3"
                    },
                    {
                        "key": "KZ2",
                        "component_id": "KZ2",
                        "component_type": "框架柱",
                        "dimensions": "400×400×3000",
                        "material": "C30",
                        "quantity": 1,
                        "unit": "根",
                        "volume": "0.48",
                        "area": "4.80",
                        "structural_role": "承重",
                        "connections": "L1, L3",
                        "location": "A2轴线交点",
                        "confidence": "94.8%",
                        "source_slice": "slice_2_4"
                    },
                    {
                        "key": "L1",
                        "component_id": "L1",
                        "component_type": "框架梁",
                        "dimensions": "300×600×6000",
                        "material": "C30",
                        "quantity": 1,
                        "unit": "根",
                        "volume": "1.08",
                        "area": "10.80",
                        "structural_role": "承重",
                        "connections": "KZ1, KZ2",
                        "location": "A轴线",
                        "confidence": "96.1%",
                        "source_slice": "slice_3_2"
                    },
                    {
                        "key": "B1",
                        "component_id": "B1",
                        "component_type": "楼板",
                        "dimensions": "120×6000×4000",
                        "material": "C25",
                        "quantity": 1,
                        "unit": "块",
                        "volume": "2.88",
                        "area": "24.00",
                        "structural_role": "承重",
                        "connections": "L1, L2, L3",
                        "location": "A-B/1-2区域",
                        "confidence": "93.7%",
                        "source_slice": "slice_1_1"
                    }
                ],
                "summary": {
                    "total_components": 4,
                    "component_types": 3,
                    "total_volume": "4.92m³",
                    "total_area": "44.40m²",
                    "component_breakdown": {
                        "框架柱": {"count": 2, "volume": 0.96, "area": 9.60},
                        "框架梁": {"count": 1, "volume": 1.08, "area": 10.80},
                        "楼板": {"count": 1, "volume": 2.88, "area": 24.00}
                    },
                    "analysis_source": "基于Vision构件识别的几何数据汇总"
                },
                "table_columns": [
                    {"title": "构件编号", "dataIndex": "component_id", "key": "component_id", "width": 120},
                    {"title": "构件类型", "dataIndex": "component_type", "key": "component_type", "width": 100},
                    {"title": "尺寸规格", "dataIndex": "dimensions", "key": "dimensions", "width": 150},
                    {"title": "材料等级", "dataIndex": "material", "key": "material", "width": 100},
                    {"title": "体积", "dataIndex": "volume", "key": "volume", "width": 80},
                    {"title": "面积", "dataIndex": "area", "key": "area", "width": 80},
                    {"title": "结构作用", "dataIndex": "structural_role", "key": "structural_role", "width": 100},
                    {"title": "置信度", "dataIndex": "confidence", "key": "confidence", "width": 80}
                ]
            }
            
            # 检查是否已存在ID为4的图纸
            existing_drawing = db.query(Drawing).filter(Drawing.id == 4).first()
            if existing_drawing:
                # 更新现有图纸
                existing_drawing.filename = "三层框架结构平面图.pdf"
                existing_drawing.status = "completed"
                existing_drawing.components_count = 14
                existing_drawing.ocr_recognition_display = json.dumps(ocr_recognition_display, ensure_ascii=False)
                existing_drawing.quantity_list_display = json.dumps(quantity_list_display, ensure_ascii=False)
                existing_drawing.updated_at = datetime.now()
                existing_drawing.user_id = test_user.id
                
                db.commit()
                print(f"✅ 更新现有图纸ID 4")
            else:
                # 创建新的图纸
                test_drawing = Drawing(
                    id=4,
                    filename="三层框架结构平面图.pdf",
                    file_path="/uploads/drawing_4_test.pdf",
                    s3_key="drawings/drawing_4_test.pdf",
                    status="completed",
                    file_size=655360,
                    file_type="pdf",
                    components_count=14,
                    ocr_recognition_display=json.dumps(ocr_recognition_display, ensure_ascii=False),
                    quantity_list_display=json.dumps(quantity_list_display, ensure_ascii=False),
                    user_id=test_user.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                db.add(test_drawing)
                db.commit()
                db.refresh(test_drawing)
                print(f"✅ 创建图纸ID 4成功")
            
            # 验证数据
            drawing_check = db.query(Drawing).filter(Drawing.id == 4).first()
            if drawing_check:
                print(f"\n🔍 数据验证:")
                print(f"   ID: {drawing_check.id}")
                print(f"   文件名: {drawing_check.filename}")
                print(f"   状态: {drawing_check.status}")
                print(f"   构件数量: {drawing_check.components_count}")
                print(f"   OCR识别块: {bool(drawing_check.ocr_recognition_display)}")
                print(f"   工程量清单块: {bool(drawing_check.quantity_list_display)}")
            
            print(f"\n🎉 图纸ID 4 双轨协同数据创建完成！")
            print(f"💡 现在可以访问 http://localhost:3000/drawings/4 查看效果")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建数据失败: {e}")
            db.rollback()
            return False
            
        finally:
            db.close()
            
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保在backend目录下运行此脚本")
        return False

if __name__ == "__main__":
    create_drawing_4_data() 