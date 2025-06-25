import sqlite3

conn = sqlite3.connect('smart_qto.db')
cursor = conn.cursor()

print("数据库中的表:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"  - {table[0]}")

conn.close() 