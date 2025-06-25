import sqlite3

# 连接数据库
conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# 获取表结构
cursor.execute("PRAGMA table_info(drawings)")
columns = cursor.fetchall()

print("drawings表结构:")
for col in columns:
    print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")

conn.close() 