#!/usr/bin/env python3
"""
检查SQLAlchemy连接的数据库和表
"""

from app.database import engine
from sqlalchemy import text

def check_database():
    print('Engine URL:', engine.url)
    
    try:
        with engine.connect() as conn:
            # 检查表
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            print('Tables:', tables)
            
            # 检查drawings表结构
            if 'drawings' in tables:
                result = conn.execute(text("PRAGMA table_info(drawings)"))
                columns = [(row[1], row[2]) for row in result.fetchall()]
                print('Drawings table columns:')
                for name, type_ in columns:
                    print(f'  {name}: {type_}')
                    
                # 检查数据
                result = conn.execute(text("SELECT COUNT(*) FROM drawings"))
                count = result.fetchone()[0]
                print(f'Drawings count: {count}')
                
                if count > 0:
                    result = conn.execute(text("SELECT id, filename, status FROM drawings LIMIT 5"))
                    for row in result.fetchall():
                        print(f'  ID {row[0]}: {row[1]} ({row[2]})')
            else:
                print('Drawings table not found!')
                
    except Exception as e:
        print('Error:', e)

if __name__ == "__main__":
    check_database() 