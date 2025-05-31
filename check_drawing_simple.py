import psycopg2
import json

try:
    # 直接使用配置值连接PostgreSQL数据库
    conn = psycopg2.connect(
        host="dbconn.sealoshzh.site",
        port=48982,
        database="postgres",
        user="postgres",
        password="2xn59xgm"
    )
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
                results = row[3]  # PostgreSQL JSON字段直接返回dict
                print('识别结果结构:')
                print(json.dumps(results, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f'识别结果解析失败: {e}')
        else:
            print('识别结果: 无')
    else:
        print('未找到ID为47的图纸')
    
    # 查看最近的几条记录
    print('\n=== 最近的图纸记录 ===')
    cursor.execute('SELECT id, filename, status, created_at FROM drawings ORDER BY created_at DESC LIMIT 5')
    rows = cursor.fetchall()
    
    for row in rows:
        print(f'ID: {row[0]}, 文件名: {row[1]}, 状态: {row[2]}, 时间: {row[3]}')
    
    conn.close()
except Exception as e:
    print(f'错误: {e}') 