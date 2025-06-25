#!/usr/bin/env python3
"""
直接在SQLite数据库中创建双轨协同测试数据
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

def create_sqlite_dual_track_data():
    """在SQLite数据库中创建双轨协同测试数据"""
    
    # 数据库文件路径
    db_path = Path(__file__).parent / "app" / "database.db"
    
    print(f"🔗 连接SQLite数据库: {db_path}")
    
    # 连接数据库
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在并添加缺失的列
        print("🔧 检查并更新表结构...")
        
        # 检查drawings表的列
        cursor.execute("PRAGMA table_info(drawings)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 添加缺失的列
        if 'ocr_recognition_display' not in columns:
            cursor.execute("ALTER TABLE drawings ADD COLUMN ocr_recognition_display TEXT")
            print("✅ 添加 ocr_recognition_display 列")
            
        if 'quantity_list_display' not in columns:
            cursor.execute("ALTER TABLE drawings ADD COLUMN quantity_list_display TEXT")
            print("✅ 添加 quantity_list_display 列")
        
        # 创建OCR识别块数据（轨道1输出点）
        ocr_recognition_display = {
            "drawing_basic_info": {
                "drawing_title": "二层柱结构配筋图",
                "drawing_number": "S-02",
                "scale": "1:100",
                "project_name": "某住宅小区A栋",
                "drawing_type": "结构施工图"
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
                "total_slices": 24,
                "ocr_text_count": 156,
                "analysis_method": "PaddleOCR + GPT-4o"
            }
        }
        
        # 创建工程量清单块数据（轨道2输出点）
        quantity_list_display = {
            "success": True,
            "components": [
                {
                    "key": "KZ1",
                    "component_id": "KZ1",
                    "component_type": "框架柱",
                    "dimensions": "400×400",
                    "material": "C30",
                    "quantity": 4,
                    "unit": "根",
                    "volume": 2.304,
                    "rebar_weight": 85.2
                },
                {
                    "key": "KZ2", 
                    "component_id": "KZ2",
                    "component_type": "框架柱",
                    "dimensions": "500×500",
                    "material": "C30",
                    "quantity": 2,
                    "unit": "根",
                    "volume": 1.8,
                    "rebar_weight": 72.5
                },
                {
                    "key": "KL1",
                    "component_id": "KL1", 
                    "component_type": "框架梁",
                    "dimensions": "300×600",
                    "material": "C30",
                    "quantity": 6,
                    "unit": "根",
                    "volume": 3.24,
                    "rebar_weight": 169.8
                }
            ],
            "summary": {
                "total_components": 9,
                "component_types": 3,
                "total_volume": "7.344 m³",
                "total_area": "23.76 m²",
                "total_concrete_volume": 7.344,
                "total_rebar_weight": 327.5,
                "total_formwork_area": 23.76,
                "component_breakdown": {
                    "框架柱": {"count": 6, "volume": 4.104, "area": 12.8},
                    "框架梁": {"count": 6, "volume": 3.24, "area": 10.96}
                },
                "analysis_source": "Vision分析 + GPT-4o"
            },
            "table_columns": [
                {"title": "构件编号", "dataIndex": "component_id", "key": "component_id"},
                {"title": "构件类型", "dataIndex": "component_type", "key": "component_type"},
                {"title": "尺寸规格", "dataIndex": "dimensions", "key": "dimensions"},
                {"title": "材料", "dataIndex": "material", "key": "material"},
                {"title": "数量", "dataIndex": "quantity", "key": "quantity"},
                {"title": "单位", "dataIndex": "unit", "key": "unit"},
                {"title": "体积(m³)", "dataIndex": "volume", "key": "volume"},
                {"title": "钢筋重量(kg)", "dataIndex": "rebar_weight", "key": "rebar_weight"}
            ]
        }
        
        # 兼容性数据（保存在recognition_results中）
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
        
        # 检查图纸是否存在
        cursor.execute("SELECT id FROM drawings WHERE id = ?", (3,))
        existing = cursor.fetchone()
        
        if existing:
            print("📝 更新现有图纸ID 3...")
            cursor.execute("""
                UPDATE drawings 
                SET ocr_recognition_display = ?,
                    quantity_list_display = ?,
                    recognition_results = ?,
                    status = 'completed',
                    components_count = ?
                WHERE id = ?
            """, (
                json.dumps(ocr_recognition_display, ensure_ascii=False),
                json.dumps(quantity_list_display, ensure_ascii=False),
                json.dumps(recognition_results, ensure_ascii=False),
                len(quantity_list_display["components"]),
                3
            ))
        else:
            print("📝 创建新图纸记录ID 3...")
            cursor.execute("""
                INSERT INTO drawings (
                    id, filename, file_path, file_type, status, 
                    ocr_recognition_display, quantity_list_display, recognition_results,
                    components_count, user_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                3,
                "test_dual_track_drawing.dwg",
                "/test/path/test_dual_track_drawing.dwg",
                "dwg",
                "completed",
                json.dumps(ocr_recognition_display, ensure_ascii=False),
                json.dumps(quantity_list_display, ensure_ascii=False),
                json.dumps(recognition_results, ensure_ascii=False),
                len(quantity_list_display["components"]),
                1,  # 假设用户ID为1
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        # 提交事务
        conn.commit()
        print("✅ 双轨协同测试数据创建成功！")
        
        # 验证数据
        cursor.execute("SELECT filename, status, ocr_recognition_display, quantity_list_display FROM drawings WHERE id = ?", (3,))
        result = cursor.fetchone()
        
        if result:
            filename, status, ocr_data, qty_data = result
            print(f"\n🔍 验证结果:")
            print(f"   文件名: {filename}")
            print(f"   状态: {status}")
            print(f"   OCR识别块: {'✅ 有数据' if ocr_data else '❌ 无数据'}")
            print(f"   工程量清单块: {'✅ 有数据' if qty_data else '❌ 无数据'}")
            
            if ocr_data:
                ocr_parsed = json.loads(ocr_data)
                print(f"   图纸标题: {ocr_parsed.get('drawing_basic_info', {}).get('drawing_title', 'N/A')}")
                
            if qty_data:
                qty_parsed = json.loads(qty_data)
                print(f"   构件数量: {len(qty_parsed.get('components', []))}")
                print(f"   总体积: {qty_parsed.get('summary', {}).get('total_concrete_volume', 0)} m³")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_sqlite_dual_track_data() 