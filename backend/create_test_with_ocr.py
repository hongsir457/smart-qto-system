import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 删除现有的测试数据
cursor.execute('DELETE FROM drawings WHERE id = 1')

# 创建包含原始OCR文本的测试数据
test_recognition_results = {
    "analysis_summary": "识别到5个框架柱构件，包含详细的尺寸和材料信息",
    "analysis_engine": "GPT-4o",
    "pipeline_type": "A→B→C数据流",
    "processing_time": "2.5秒",
    
    # 原始OCR识别的文本数据
    "ocr_texts": [
        "框架柱 K-JKZT 400×400 C30",
        "框架柱 K-JIZ 500×500 C30混凝土",
        "K-JKZ2 450×450 C30",
        "框架柱K-JKZ1a 400×600 C30混凝土",
        "K-JKZ3 350×350 C30",
        "钢筋混凝土",
        "结构平面图",
        "比例 1:100",
        "图号 S-01",
        "设计 张工",
        "审核 李工",
        "2025年1月"
    ],
    
    # 结构化的构件数据
    "components": [
        {
            "component_id": "K-JKZT",
            "component_type": "框架柱",
            "dimensions": "400×400",
            "material": "C30混凝土",
            "quantity": 8,
            "unit": "根"
        },
        {
            "component_id": "K-JIZ", 
            "component_type": "框架柱",
            "dimensions": "500×500",
            "material": "C30混凝土",
            "quantity": 4,
            "unit": "根"
        },
        {
            "component_id": "K-JKZ2",
            "component_type": "框架柱", 
            "dimensions": "450×450",
            "material": "C30混凝土",
            "quantity": 6,
            "unit": "根"
        },
        {
            "component_id": "K-JKZ1a",
            "component_type": "框架柱",
            "dimensions": "400×600", 
            "material": "C30混凝土",
            "quantity": 2,
            "unit": "根"
        },
        {
            "component_id": "K-JKZ3",
            "component_type": "框架柱",
            "dimensions": "350×350",
            "material": "C30混凝土", 
            "quantity": 10,
            "unit": "根"
        }
    ],
    
    # 工程量汇总
    "quantities": {
        "框架柱": {
            "total_count": 30,
            "total_volume": "45.6m³",
            "details": [
                {"type": "K-JKZT 400×400", "count": 8, "volume": "12.8m³"},
                {"type": "K-JIZ 500×500", "count": 4, "volume": "10.0m³"},
                {"type": "K-JKZ2 450×450", "count": 6, "volume": "12.2m³"},
                {"type": "K-JKZ1a 400×600", "count": 2, "volume": "4.8m³"},
                {"type": "K-JKZ3 350×350", "count": 10, "volume": "12.3m³"}
            ]
        }
    }
}

# 插入测试数据 - 使用正确的列名
cursor.execute('''
    INSERT INTO drawings (
        id, filename, file_path, file_type, file_size, 
        status, recognition_results, components_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (
    1,
    '测试建筑结构图纸.pdf',
    '/uploads/test_drawing.pdf',
    'pdf',
    655360,  # 0.62 MB in bytes
    'completed',
    json.dumps(test_recognition_results, ensure_ascii=False),
    5
))

conn.commit()
conn.close()

print("✅ 已创建包含原始OCR文本的测试数据")
print("📋 包含12条原始OCR文本和5个结构化构件")
print("🔍 可用于自然语言显示测试") 