from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database import SessionLocal
from app.models.user import User
import asyncio  # 导入 asyncio

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def get_db() -> Generator:
    """
    获取数据库会话
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def _get_user_from_token(token: str, db: Session) -> Optional[User]:
    """
    从token解码并获取用户的核心逻辑（可重用）。
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        
        user_id = int(user_id_str)
        return db.query(User).filter(User.id == user_id).first()
        
    except (JWTError, ValueError, TypeError):
        return None

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    获取当前用户，支持测试模式
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    print("get_current_user, token:", token)
    
    # 测试模式支持
    if token == "test_token_for_development":
        print("使用测试token，返回真实用户")
        # 返回真实用户ID=2 (hongsir)，而不是测试用户
        real_user = db.query(User).filter(User.id == 2).first()
        if not real_user:
            # 如果真实用户不存在，才使用测试用户
            real_user = db.query(User).filter(User.id == 1).first()
            if not real_user:
                print("创建新的测试用户")
                real_user = User(
                    username="test_user_dev",
                    email="test_dev@example.com",
                    hashed_password="test_password_hash",
                    is_active=True
                )
                db.add(real_user)
                db.commit()
                db.refresh(real_user)
        
        print("返回真实用户:", real_user.username if real_user else "None")
        return real_user
    
    # 正常JWT验证流程
    user = _get_user_from_token(token, db)
    if not user:
        raise credentials_exception
    print("get_current_user, user:", user)
    return user

async def get_current_user_websocket(token: str) -> Optional[User]:
    """
    WebSocket专用的用户认证函数
    """
    def sync_db_call():
        """将所有同步DB操作包装在这个函数内"""
        db = SessionLocal()
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            
            user = db.query(User).filter(User.id == int(user_id)).first()
            return user
        except (JWTError, ValueError):
            return None
        finally:
            db.close()

    try:
        # 使用 to_thread 在单独的线程中运行同步的数据库代码
        user = await asyncio.to_thread(sync_db_call)
        if user is None:
            print("WebSocket auth failed: Could not validate credentials.")
        return user
    except Exception as e:
        print(f"Error in get_current_user_websocket: {e}")
        return None

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user 