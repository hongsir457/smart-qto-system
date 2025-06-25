#!/usr/bin/env python3
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_test_user():
    db = SessionLocal()
    try:
        # 检查是否已存在测试用户
        existing_user = db.query(User).filter(User.username == 'test_user').first()
        if existing_user:
            print('测试用户已存在:', existing_user.username, 'ID:', existing_user.id)
            return existing_user
        else:
            # 创建测试用户
            test_user = User(
                username='test_user',
                email='test_user_unique@example.com',
                hashed_password=get_password_hash('test123'),
                is_active=True
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print('测试用户创建成功:', test_user.username, 'ID:', test_user.id)
            return test_user
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user() 