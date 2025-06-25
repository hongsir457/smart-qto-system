import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 为ID=2创建新的测试数据
test_recognition_results_id2 = {
    "analysis_summary": "识别到7个梁构件和3个柱构件，包含详细的尺寸和材料信息",
    "analysis_engine": "GPT-4o",
    "pipeline_type": "A→B→C数据流",
    "processing_time": "3.2秒",
    
    # 原始OCR识别的文本数据
    "ocr_texts": [
        "主梁 L-1 400×800 C35",
        "次梁 L-2 300×600 C35混凝土",
        "L-3 350×700 C35",
        "框架柱 KZ-1 600×600 C35混凝土",
        "KZ-2 500×500 C35",
        "KZ-3 400×400 C35",
        "钢筋混凝土结构",
        "二层结构平面图",
        "比例 1:150",
        "图号 S-02",
        "项目 办公楼改造",
        "设计 王工",
        "校对 刘工",
        "审核 陈工",
        "2025年2月"
    ],
    
    # 结构化的构件数据
    "components": [
        {
            "component_id": "L-1",
            "component_type": "主梁",
            "dimensions": "400×800",
            "material": "C35混凝土",
            "quantity": 12,
            "unit": "根"
        },
        {
            "component_id": "L-2", 
            "component_type": "次梁",
            "dimensions": "300×600",
            "material": "C35混凝土",
            "quantity": 18,
            "unit": "根"
        },
        {
            "component_id": "L-3",
            "component_type": "次梁", 
            "dimensions": "350×700",
            "material": "C35混凝土",
            "quantity": 8,
            "unit": "根"
        },
        {
            "component_id": "KZ-1",
            "component_type": "框架柱",
            "dimensions": "600×600", 
            "material": "C35混凝土",
            "quantity": 6,
            "unit": "根"
        },
        {
            "component_id": "KZ-2",
            "component_type": "框架柱",
            "dimensions": "500×500",
            "material": "C35混凝土", 
            "quantity": 8,
            "unit": "根"
        },
        {
            "component_id": "KZ-3",
            "component_type": "框架柱",
            "dimensions": "400×400",
            "material": "C35混凝土", 
            "quantity": 4,
            "unit": "根"
        }
    ],
    
    # 工程量汇总
    "quantities": {
        "主梁": {
            "total_count": 12,
            "total_volume": "38.4m³"
        },
        "次梁": {
            "total_count": 26, 
            "total_volume": "68.2m³"
        },
        "框架柱": {
            "total_count": 18,
            "total_volume": "52.8m³"
        }
    }
}

# 为ID=3更新OCR文本数据
test_recognition_results_id3 = {
    "analysis_summary": "识别到5个框架柱构件的改造加固信息",
    "analysis_engine": "GPT-4o",
    "pipeline_type": "A→B→C数据流",
    "processing_time": "2.8秒",
    
    # 原始OCR识别的文本数据
    "ocr_texts": [
        "加固柱 JGZ-1 原400×400 加固至500×500",
        "加固柱 JGZ-2 原350×350 加固至450×450", 
        "JGZ-3 原500×500 增设钢板",
        "新增柱 XZ-1 400×600 C40",
        "新增柱 XZ-2 350×350 C40混凝土",
        "加固材料 Q345钢板",
        "植筋胶 HRB400",
        "一层柱结构改造加固平面图",
        "比例 1:100",
        "图号 JG-01", 
        "项目 旧楼加固改造",
        "设计 张工程师",
        "审核 李总工",
        "2025年1月施工"
    ],
    
    # 结构化的构件数据
    "components": [
        {
            "component_id": "JGZ-1",
            "component_type": "加固柱",
            "dimensions": "400×400→500×500",
            "material": "原C30+新增C40",
            "quantity": 6,
            "unit": "根"
        },
        {
            "component_id": "JGZ-2", 
            "component_type": "加固柱",
            "dimensions": "350×350→450×450",
            "material": "原C30+新增C40",
            "quantity": 4,
            "unit": "根"
        },
        {
            "component_id": "JGZ-3",
            "component_type": "加固柱", 
            "dimensions": "500×500+钢板",
            "material": "C30+Q345钢板",
            "quantity": 2,
            "unit": "根"
        },
        {
            "component_id": "XZ-1",
            "component_type": "新增柱",
            "dimensions": "400×600", 
            "material": "C40混凝土",
            "quantity": 3,
            "unit": "根"
        },
        {
            "component_id": "XZ-2",
            "component_type": "新增柱",
            "dimensions": "350×350",
            "material": "C40混凝土", 
            "quantity": 2,
            "unit": "根"
        }
    ]
}

# 删除现有的ID=2数据（如果存在）
cursor.execute('DELETE FROM drawings WHERE id = 2')

# 插入ID=2的测试数据
cursor.execute('''
    INSERT INTO drawings (
        id, filename, file_path, file_type, file_size, 
        status, recognition_results, components_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (
    2,
    '二层结构平面图.pdf',
    '/uploads/floor2_structure.pdf',
    'pdf',
    892160,  # 0.85 MB in bytes
    'completed',
    json.dumps(test_recognition_results_id2, ensure_ascii=False),
    6
))

# 更新ID=3的数据，添加OCR文本
cursor.execute('''
    UPDATE drawings 
    SET recognition_results = ?, components_count = ?
    WHERE id = 3
''', (
    json.dumps(test_recognition_results_id3, ensure_ascii=False),
    5
))

conn.commit()
conn.close()

print("✅ 已创建ID=2的测试数据")
print("✅ 已更新ID=3的OCR文本数据")
print("📋 ID=2: 6个构件 (主梁+次梁+框架柱)")
print("📋 ID=3: 5个构件 (加固柱+新增柱)")
print("🔍 两个图纸都包含完整的OCR文本用于自然语言显示") 