import sqlite3
import json

# 连接数据库
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 查询ID=2和ID=3的数据
cursor.execute('SELECT id, filename, recognition_results FROM drawings WHERE id IN (2, 3)')
results = cursor.fetchall()

for result in results:
    drawing_id, filename, recognition_results = result
    
    if recognition_results:
        data = json.loads(recognition_results)
        ocr_texts = data.get('ocr_texts', [])
        components = data.get('components', [])
        
        print(f"图纸ID: {drawing_id}")
        print(f"文件名: {filename}")
        print(f"OCR文本数: {len(ocr_texts)}")
        print(f"构件数: {len(components)}")
        
        if ocr_texts:
            print("前3条OCR文本:")
            for i, text in enumerate(ocr_texts[:3]):
                print(f"  {i+1}. {text}")
        print("=" * 50)

conn.close() 