import sqlite3
import json
import os

# 连接数据库
db_path = os.path.join('app', 'database.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询图纸ID=3的详细数据
cursor.execute('SELECT recognition_results, processing_result FROM drawings WHERE id = 3')
result = cursor.fetchone()

output_file = 'drawing_3_data.json'

if result:
    recognition_results_str, processing_result_str = result
    
    data_to_dump = {}
    
    print("✅ 成功查询到图纸ID=3的数据")
    
    if recognition_results_str:
        print("🔍 recognition_results 字段不为空，正在解析...")
        try:
            data_to_dump['recognition_results'] = json.loads(recognition_results_str)
            print("  - recognition_results 解析成功")
        except json.JSONDecodeError as e:
            print(f"  - recognition_results 解析失败: {e}")
            data_to_dump['recognition_results'] = recognition_results_str
    else:
        print("⚠️ recognition_results 字段为空")

    if processing_result_str:
        print("🔍 processing_result 字段不为空，正在解析...")
        try:
            data_to_dump['processing_result'] = json.loads(processing_result_str)
            print("  - processing_result 解析成功")
        except json.JSONDecodeError as e:
            print(f"  - processing_result 解析失败: {e}")
            data_to_dump['processing_result'] = processing_result_str
    else:
        print("⚠️ processing_result 字段为空")
        
    # 将数据写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data_to_dump, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ 已将图纸ID=3的详细数据导出到文件: {output_file}")

else:
    print('❌ 未找到图纸ID=3的数据')

conn.close() 