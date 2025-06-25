"""
WebSocket V2 API 端点
使用 WebSocketManager 连接池的新版本端点
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.services.websocket_service_v2 import get_websocket_service_v2
from app.models.user import User
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_user_from_websocket_token(token: str, db: Session) -> User:
    """从 WebSocket token 获取用户信息"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的token")
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="无效的token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return user


@router.websocket("/tasks/{user_id}")
async def websocket_task_status_v2(websocket: WebSocket, user_id: int, token: Optional[str] = None):
    """
    WebSocket V2 任务状态端点
    使用连接池管理器的新版本
    
    Args:
        websocket: WebSocket 连接
        user_id: 用户ID
        token: JWT认证token
    """
    await websocket.accept()
    
    try:
        # 验证用户权限
        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "缺少认证token",
                "code": "AUTH_REQUIRED"
            })
            await websocket.close()
            return
        
        # 验证token和用户
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            user = await get_user_from_websocket_token(token, db)
            
            # 验证用户ID匹配
            if user.id != user_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "用户ID不匹配",
                    "code": "USER_MISMATCH"
                })
                await websocket.close()
                return
                
        except HTTPException as e:
            await websocket.send_json({
                "type": "error",
                "message": e.detail,
                "code": "AUTH_FAILED"
            })
            await websocket.close()
            return
        finally:
            db.close()
        
        # 使用 WebSocket 服务处理连接
        websocket_service = get_websocket_service_v2()
        await websocket_service.handle_connection(websocket, user_id, "task_status")
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket 任务状态连接断开: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket 任务状态异常: user={user_id}, error={e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"连接异常: {str(e)}",
                "code": "CONNECTION_ERROR"
            })
        except:
            pass


@router.websocket("/notifications/{user_id}")
async def websocket_notifications_v2(websocket: WebSocket, user_id: int, token: Optional[str] = None):
    """
    WebSocket V2 通知端点
    用于接收系统通知
    
    Args:
        websocket: WebSocket 连接
        user_id: 用户ID
        token: JWT认证token
    """
    await websocket.accept()
    
    try:
        # 验证认证（简化版本）
        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "缺少认证token"
            })
            await websocket.close()
            return
        
        # 使用 WebSocket 服务处理连接
        websocket_service = get_websocket_service_v2()
        await websocket_service.handle_connection(websocket, user_id, "notifications")
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket 通知连接断开: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket 通知异常: user={user_id}, error={e}", exc_info=True)


@router.websocket("/admin/monitor")
async def websocket_admin_monitor(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket V2 管理监控端点
    用于管理员监控所有连接
    
    Args:
        websocket: WebSocket 连接
        token: JWT认证token
    """
    await websocket.accept()
    
    try:
        # 验证管理员权限（简化）
        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "管理员权限验证失败"
            })
            await websocket.close()
            return
        
        # 使用特殊用户ID（-1表示管理员）
        websocket_service = get_websocket_service_v2()
        await websocket_service.handle_connection(websocket, -1, "admin_monitor")
        
    except WebSocketDisconnect:
        logger.info("WebSocket 管理监控连接断开")
    except Exception as e:
        logger.error(f"WebSocket 管理监控异常: {e}", exc_info=True)


# 添加连接状态查询端点
from fastapi import Depends as FastAPIDepends
from app.api.deps import get_current_user

@router.get("/stats")
async def get_websocket_stats(current_user: User = FastAPIDepends(get_current_user)):
    """
    获取 WebSocket 连接统计信息
    """
    try:
        websocket_service = get_websocket_service_v2()
        stats = websocket_service.get_connection_stats()
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取WebSocket统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/connections/{user_id}")
async def get_user_connections(
    user_id: int,
    current_user: User = FastAPIDepends(get_current_user)
):
    """
    获取用户的 WebSocket 连接信息
    """
    try:
        # 权限检查：用户只能查看自己的连接
        if current_user.id != user_id and not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=403,
                detail="无权限查看其他用户的连接信息"
            )
        
        websocket_service = get_websocket_service_v2()
        connections = websocket_service.get_user_connections_info(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "connections": connections,
                "count": len(connections)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户连接信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取连接信息失败: {str(e)}"
        ) 