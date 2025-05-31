import sqlite3
import json

try:
    conn = sqlite3.connect('app/database.db')
    cursor = conn.cursor()
    
    # 查看ID为47的图纸数据
    cursor.execute('SELECT id, filename, status, recognition_results FROM drawings WHERE id = 47')
    row = cursor.fetchone()
    
    if row:
        print(f'图纸ID: {row[0]}')
        print(f'文件名: {row[1]}')
        print(f'状态: {row[2]}')
        
        if row[3]:
            try:
                results = json.loads(row[3])
                print('识别结果结构:')
                print(json.dumps(results, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f'识别结果解析失败: {e}')
        else:
            print('识别结果: 无')
    else:
        print('未找到ID为47的图纸')
    
    conn.close()
except Exception as e:
    print(f'错误: {e}') 