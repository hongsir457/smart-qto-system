import sqlite3
import json

# 直接连接SQLite数据库
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# 查询图纸1的数据
cursor.execute("SELECT id, filename, status, processing_result FROM drawings WHERE id = 1")
row = cursor.fetchone()

if row:
    drawing_id, filename, status, processing_result_str = row
    print(f"图纸ID: {drawing_id}")
    print(f"文件名: {filename}")
    print(f"状态: {status}")
    print()
    
    if processing_result_str:
        try:
            processing_result = json.loads(processing_result_str)
            print("processing_result字段:")
            
            # 检查A→B→C字段
            abc_fields = ['result_a_raw_ocr', 'result_b_corrected_json', 'result_c_human_readable']
            for field in abc_fields:
                if field in processing_result:
                    field_data = processing_result[field]
                    if isinstance(field_data, dict) and 's3_url' in field_data:
                        print(f"  {field}: ✅ {field_data['s3_url']}")
                    else:
                        print(f"  {field}: ❌ (存在但格式错误: {type(field_data)})")
                else:
                    print(f"  {field}: ❌ (不存在)")
            
            # 检查兼容字段
            if 'human_readable_txt' in processing_result:
                hrt = processing_result['human_readable_txt']
                if isinstance(hrt, dict) and 's3_url' in hrt:
                    print(f"  human_readable_txt: ✅ {hrt['s3_url']}")
                else:
                    print(f"  human_readable_txt: ❌ (格式错误)")
            else:
                print("  human_readable_txt: ❌ (不存在)")
                
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
    else:
        print("processing_result为空")
else:
    print("未找到图纸1")

conn.close() 