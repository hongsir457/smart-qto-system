#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查和修复数据库schema脚本
"""

import sqlite3
import os

def check_and_fix_database():
    """检查并修复数据库表结构"""
    db_path = "app/database.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
        
    print(f"🔍 检查数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查drawings表的当前结构
        cursor.execute("PRAGMA table_info(drawings)")
        columns = cursor.fetchall()
        
        print("📋 当前drawings表结构:")
        column_names = []
        for col in columns:
            print(f"   {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
            column_names.append(col[1])
        
        # 检查需要添加的字段
        required_fields = {
            'ocr_merged_result_key': 'VARCHAR',
            'ocr_corrected_result_key': 'VARCHAR', 
            'ocr_correction_summary': 'JSON'
        }
        
        missing_fields = []
        for field, field_type in required_fields.items():
            if field not in column_names:
                missing_fields.append((field, field_type))
        
        if missing_fields:
            print(f"\n⚠️ 缺少字段: {len(missing_fields)} 个")
            for field, field_type in missing_fields:
                print(f"   - {field} ({field_type})")
            
            # 添加缺少的字段
            print("\n🔧 开始添加缺少的字段...")
            for field, field_type in missing_fields:
                try:
                    alter_sql = f"ALTER TABLE drawings ADD COLUMN {field} {field_type}"
                    cursor.execute(alter_sql)
                    print(f"   ✅ 添加字段: {field}")
                except Exception as e:
                    print(f"   ❌ 添加字段失败 {field}: {e}")
            
            conn.commit()
            print("✅ 字段添加完成")
        else:
            print("✅ 所有必需字段都存在")
        
        # 再次检查表结构
        cursor.execute("PRAGMA table_info(drawings)")
        columns = cursor.fetchall()
        
        print("\n📋 修复后的drawings表结构:")
        for col in columns:
            is_new = col[1] in [field for field, _ in required_fields.items()]
            status = "🆕" if is_new else "  "
            print(f"   {status} {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = check_and_fix_database()
    print(f"\n🎯 数据库检查结果: {'成功' if success else '失败'}")
    exit(0 if success else 1) 