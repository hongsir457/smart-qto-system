# -*- coding: utf-8 -*-
"""
用户CRUD操作
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from ..services.auth import get_password_hash, verify_password

def get_user(db: Session, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """获取用户列表"""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate) -> User:
    """创建用户"""
    # 检查用户名是否已存在
    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建用户
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=getattr(user, 'full_name', None),
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """更新用户信息"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    # 更新用户字段
    update_data = user_update.dict(exclude_unset=True)
    
    # 如果有密码更新，需要哈希处理
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # 检查用户名是否已被其他用户使用
    if "username" in update_data:
        existing_user = get_user_by_username(db, update_data["username"])
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被其他用户使用"
            )
    
    # 检查邮箱是否已被其他用户使用
    if "email" in update_data:
        existing_user = get_user_by_email(db, update_data["email"])
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用"
            )
    
    # 更新用户信息
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """删除用户"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    
    return True

def activate_user(db: Session, user_id: int) -> Optional[User]:
    """激活用户"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db_user.is_active = True
    db.commit()
    db.refresh(db_user)
    
    return db_user

def deactivate_user(db: Session, user_id: int) -> Optional[User]:
    """停用用户"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    db_user.is_active = False
    db.commit()
    db.refresh(db_user)
    
    return db_user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户凭据"""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
    """修改用户密码"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    # 验证旧密码
    if not verify_password(old_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    # 更新密码
    db_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return True

def reset_password(db: Session, username: str, email: str, new_password: str) -> bool:
    """重置用户密码"""
    db_user = get_user_by_username(db, username)
    if not db_user or db_user.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名和邮箱不匹配"
        )
    
    # 更新密码
    db_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return True

def get_user_stats(db: Session, user_id: int) -> dict:
    """获取用户统计信息"""
    from ..models.drawing import Drawing
    from ..models.task import Task
    
    db_user = get_user(db, user_id)
    if not db_user:
        return {}
    
    # 统计图纸数量
    drawings_count = db.query(Drawing).filter(Drawing.user_id == user_id).count()
    
    # 统计任务数量
    tasks_count = db.query(Task).filter(Task.user_id == user_id).count()
    completed_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.status == "completed"
    ).count()
    
    return {
        "user_id": user_id,
        "username": db_user.username,
        "drawings_count": drawings_count,
        "tasks_count": tasks_count,
        "completed_tasks": completed_tasks,
        "success_rate": completed_tasks / tasks_count if tasks_count > 0 else 0,
        "is_active": db_user.is_active,
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None
    } 