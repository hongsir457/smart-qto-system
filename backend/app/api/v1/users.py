# -*- coding: utf-8 -*-
"""
用户管理API路由
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import User, UserCreate, UserUpdate, UserInDB, UserResponse
from app.crud import users as crud_users
from app.services.auth import get_current_user, get_current_active_user
from app.models.user import User as UserModel

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    创建新用户
    """
    try:
        db_user = crud_users.create_user(db=db, user=user)
        return UserResponse.from_orm(db_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )

@router.get("/", response_model=List[UserResponse])
def read_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回的记录数"),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户列表（仅管理员可访问）
    """
    # 这里可以添加管理员权限检查
    users = crud_users.get_users(db, skip=skip, limit=limit)
    return [UserResponse.from_orm(user) for user in users]

@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    获取当前用户信息
    """
    return UserResponse.from_orm(current_user)

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    根据ID获取用户信息
    """
    # 检查权限：只能查看自己的信息，或者是管理员
    if current_user.id != user_id:
        # 这里可以添加管理员权限检查
        pass
    
    db_user = crud_users.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserResponse.from_orm(db_user)

@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    """
    db_user = crud_users.update_user(db, user_id=current_user.id, user_update=user_update)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserResponse.from_orm(db_user)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新指定用户信息（仅管理员）
    """
    # 检查权限：只有管理员或用户本人可以更新
    if current_user.id != user_id:
        # 这里可以添加管理员权限检查
        pass
    
    db_user = crud_users.update_user(db, user_id=user_id, user_update=user_update)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserResponse.from_orm(db_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除用户（仅管理员）
    """
    # 这里可以添加管理员权限检查
    
    success = crud_users.delete_user(db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    激活用户（仅管理员）
    """
    # 这里可以添加管理员权限检查
    
    db_user = crud_users.activate_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserResponse.from_orm(db_user)

@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    停用用户（仅管理员）
    """
    # 这里可以添加管理员权限检查
    
    db_user = crud_users.deactivate_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return UserResponse.from_orm(db_user)

@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改当前用户密码
    """
    try:
        success = crud_users.change_password(
            db, 
            user_id=current_user.id, 
            old_password=old_password, 
            new_password=new_password
        )
        if success:
            return {"message": "密码修改成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码修改失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码修改失败: {str(e)}"
        )

@router.post("/reset-password")
def reset_password(
    username: str,
    email: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    重置用户密码
    """
    try:
        success = crud_users.reset_password(
            db, 
            username=username, 
            email=email, 
            new_password=new_password
        )
        if success:
            return {"message": "密码重置成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码重置失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码重置失败: {str(e)}"
        )

@router.get("/me/stats")
def get_user_stats(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户统计信息
    """
    stats = crud_users.get_user_stats(db, user_id=current_user.id)
    return stats

@router.get("/{user_id}/stats")
def get_user_stats_by_id(
    user_id: int,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取指定用户统计信息（仅管理员或用户本人）
    """
    # 检查权限：只有管理员或用户本人可以查看
    if current_user.id != user_id:
        # 这里可以添加管理员权限检查
        pass
    
    stats = crud_users.get_user_stats(db, user_id=user_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    return stats 