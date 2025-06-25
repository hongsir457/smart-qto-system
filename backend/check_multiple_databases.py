#!/usr/bin/env python3
"""
检查系统中的多个数据库文件
"""

import sqlite3
import os
from pathlib import Path
from app.core.config import settings
from app.database import engine

def check_multiple_databases():
    """检查系统中的多个数据库文件"""
    
    print("检查系统中的多个数据库文件")
    print("="*60)
    
    # 检查配置
    print("数据库配置:")
    print(f"   settings.DATABASE_URL: {settings.DATABASE_URL}")
    print(f"   SQLAlchemy引擎URL: {engine.url}")
    print()
    
    # 数据库文件列表
    base_dir = Path(__file__).parent
    db_files = [
        base_dir / "app.db",
        base_dir / "smart_qto.db", 
        base_dir / "app" / "database.db",
        base_dir / "app" / "database_backup.db",
        base_dir / "app" / "database_old.db"
    ]
    
    for db_file in db_files:
        if db_file.exists():
            size = db_file.stat().st_size
            print(f"=== {db_file.name} ===")
            print(f"   路径: {db_file}")
            print(f"   大小: {size:,} 字节")
            
            if size > 0:
                try:
                    conn = sqlite3.connect(str(db_file))
                    cursor = conn.cursor()
                    
                    # 检查表
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    print(f"   表: {tables}")
                    
                    # 检查drawings表
                    if 'drawings' in tables:
                        cursor.execute("SELECT COUNT(*) FROM drawings")
                        count = cursor.fetchone()[0]
                        print(f"   drawings记录数: {count}")
                        
                        if count > 0:
                            cursor.execute("SELECT id, filename, status FROM drawings ORDER BY id LIMIT 5")
                            print("   前5条记录:")
                            for row in cursor.fetchall():
                                print(f"     ID {row[0]}: {row[1]} ({row[2]})")
                        
                        # 检查是否有双轨协同字段
                        cursor.execute("PRAGMA table_info(drawings)")
                        columns = [row[1] for row in cursor.fetchall()]
                        has_ocr_display = 'ocr_recognition_display' in columns
                        has_qty_display = 'quantity_list_display' in columns
                        print(f"   ocr_recognition_display字段: {'有' if has_ocr_display else '无'}")
                        print(f"   quantity_list_display字段: {'有' if has_qty_display else '无'}")
                        
                        # 检查图纸ID 3的数据
                        if count > 0:
                            cursor.execute("SELECT id, ocr_recognition_display, quantity_list_display FROM drawings WHERE id = 3")
                            result = cursor.fetchone()
                            if result:
                                id_, ocr_data, qty_data = result
                                print(f"   图纸ID 3:")
                                print(f"     OCR识别块: {'有数据' if ocr_data else '无数据'}")
                                print(f"     工程量清单块: {'有数据' if qty_data else '无数据'}")
                            else:
                                print(f"   图纸ID 3: 不存在")
                    
                    conn.close()
                    
                except Exception as e:
                    print(f"   错误: {e}")
            else:
                print("   空文件")
            print()
        else:
            print(f"=== {db_file.name} ===")
            print("   文件不存在")
            print()
    
    # 检查当前SQLAlchemy连接的数据库
    print("当前SQLAlchemy连接检查:")
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"   连接的数据库表: {tables}")
            
            if 'drawings' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM drawings"))
                count = result.fetchone()[0]
                print(f"   drawings记录数: {count}")
                
                if count > 0:
                    result = conn.execute(text("SELECT id, filename FROM drawings WHERE id = 3"))
                    row = result.fetchone()
                    if row:
                        print(f"   图纸ID 3: {row[1]}")
                    else:
                        print(f"   图纸ID 3: 不存在")
    except Exception as e:
        print(f"   SQLAlchemy连接错误: {e}")

if __name__ == "__main__":
    check_multiple_databases() 