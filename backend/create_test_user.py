#!/usr/bin/env python3
"""
创建测试用户和验证数据
"""

from app.database import SessionLocal
from app.models.user import User
from app.models.drawing import Drawing

def create_test_user_and_verify():
    db = SessionLocal()
    try:
        # 创建测试用户
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            user = User(
                id=1,
                username='testuser',
                email='test@example.com',
                hashed_password='dummy_hash'
            )
            db.add(user)
            db.commit()
            print('✅ 测试用户创建成功')
        else:
            print('✅ 测试用户已存在')
        
        # 检查图纸数据
        drawing = db.query(Drawing).filter(Drawing.id == 3).first()
        if drawing:
            print(f'✅ 图纸ID 3存在: {drawing.filename}')
            print(f'   状态: {drawing.status}')
            has_ocr = bool(drawing.ocr_recognition_display)
            has_qty = bool(drawing.quantity_list_display)
            print(f'   OCR识别块: {"有数据" if has_ocr else "无数据"}')
            print(f'   工程量清单块: {"有数据" if has_qty else "无数据"}')
            print(f'   构件数量: {drawing.components_count or 0}')
        else:
            print('❌ 图纸ID 3不存在')
            
    except Exception as e:
        print(f'❌ 操作失败: {e}')
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user_and_verify() 