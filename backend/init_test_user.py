#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
sys.path.append('.')
from app.database import SessionLocal, engine, Base
from app.models.user import User  
from app.core.security import get_password_hash

try:
    # 创建表
    Base.metadata.create_all(bind=engine)
    print('✅ 数据库表创建成功')
    
    # 创建测试用户
    db = SessionLocal()
    existing_user = db.query(User).filter(User.username == 'testuser').first()
    
    if not existing_user:
        test_user = User(
            username='testuser',
            email='test@example.com',
            full_name='测试用户',
            hashed_password=get_password_hash('testpass123'),
            is_active=True
        )
        db.add(test_user)
        db.commit()
        print('✅ 测试用户创建成功: testuser / testpass123')
    else:
        print('✅ 测试用户已存在')
    
    db.close()
    
except Exception as e:
    print(f'❌ 初始化失败: {str(e)}') 