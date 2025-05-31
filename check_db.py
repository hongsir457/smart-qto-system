import sqlite3
import json

def check_drawings():
    try:
        conn = sqlite3.connect('app/database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, status, file_type, created_at, recognition_results 
            FROM drawings 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        
        print("=== 最近上传的图纸 ===")
        for row in cursor.fetchall():
            print(f"ID: {row[0]}")
            print(f"文件名: {row[1]}")
            print(f"状态: {row[2]}")
            print(f"类型: {row[3]}")
            print(f"时间: {row[4]}")
            
            if row[5]:
                try:
                    results = json.loads(row[5])
                    print("识别结果存在:")
                    if 'quantities' in results:
                        quantities = results['quantities']
                        if 'total' in quantities:
                            total = quantities['total']
                            print(f"  - 总工程量: {total}")
                        else:
                            print("  - 缺少total字段")
                    else:
                        print("  - 缺少quantities字段")
                except json.JSONDecodeError:
                    print("  - 识别结果解析失败")
            else:
                print("识别结果: 无")
            print("-" * 50)
        
        conn.close()
        
    except Exception as e:
        print(f"数据库检查错误: {e}")

if __name__ == "__main__":
    check_drawings() 