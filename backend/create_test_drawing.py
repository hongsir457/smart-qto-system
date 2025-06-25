#!/usr/bin/env python3
"""
创建测试图纸数据，包含构件清单信息
"""

import json
from datetime import datetime
from app.database import SessionLocal
from app.models.drawing import Drawing

def create_test_drawing():
    """创建包含构件清单的测试图纸"""
    
    # 模拟构件清单数据
    components_data = [
        {
            "component_id": "K-JKZT",
            "component_type": "框架柱",
            "dimensions": "400×400",
            "material": "C30混凝土",
            "quantity": 1,
            "unit": "根"
        },
        {
            "component_id": "K-JIZ", 
            "component_type": "框架柱",
            "dimensions": "500×500",
            "material": "C30混凝土",
            "quantity": 1,
            "unit": "根"
        },
        {
            "component_id": "K-JKZ2",
            "component_type": "框架柱", 
            "dimensions": "450×450",
            "material": "C30混凝土",
            "quantity": 1,
            "unit": "根"
        },
        {
            "component_id": "K-JKZ1a",
            "component_type": "框架柱",
            "dimensions": "400×600",
            "material": "C30混凝土", 
            "quantity": 1,
            "unit": "根"
        },
        {
            "component_id": "K-JKZ3",
            "component_type": "框架柱",
            "dimensions": "350×350",
            "material": "C30混凝土",
            "quantity": 1,
            "unit": "根"
        }
    ]
    
    # 模拟识别结果数据
    recognition_results = {
        "analysis_summary": {
            "total_ocr_texts": 136,
            "successful_images": 1,
            "total_components": len(components_data),
            "total_dimensions": 15
        },
        "analysis_engine": "UnifiedOCREngine + GPT-4o",
        "pipeline_type": "OCR + AI分析 + 构件识别",
        "processing_time": 45.2,
        "components": components_data,
        "quantities": {
            "concrete_volume": 12.5,
            "steel_weight": 850.3,
            "formwork_area": 45.8,
            "calculation_engine": "UnifiedQuantityEngine"
        }
    }
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 创建测试图纸
        test_drawing = Drawing(
            filename="测试建筑结构图纸.pdf",
            file_path="/uploads/test_drawing.pdf",
            s3_key="drawings/test_drawing.pdf",
            status="completed",
            file_size=2048000,  # 2MB
            file_type="application/pdf",
            components_count=len(components_data),
            recognition_results=json.dumps(recognition_results, ensure_ascii=False),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 保存到数据库
        db.add(test_drawing)
        db.commit()
        db.refresh(test_drawing)
        
        print(f"✅ 成功创建测试图纸:")
        print(f"   ID: {test_drawing.id}")
        print(f"   文件名: {test_drawing.filename}")
        print(f"   状态: {test_drawing.status}")
        print(f"   构件数量: {test_drawing.components_count}")
        print(f"   创建时间: {test_drawing.created_at}")
        
        return test_drawing.id
        
    except Exception as e:
        print(f"❌ 创建测试图纸失败: {e}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    drawing_id = create_test_drawing()
    if drawing_id:
        print(f"\n🎉 测试图纸创建成功！")
        print(f"📋 可以在前端访问: http://localhost:3000/drawings/{drawing_id}")
        print(f"🔍 构件清单将显示在OCR识别结果块中")
    else:
        print(f"\n❌ 测试图纸创建失败") 