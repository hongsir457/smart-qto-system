"""
重构后的WebSocket路由模块
统一管理所有WebSocket端点，路径前缀为 /api/v1/ws/
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from ...database import get_db
from ..deps import get_current_user_websocket
from ...models.user import User
from ...services.websocket_service import WebSocketService
from ...tasks import task_manager

logger = logging.getLogger(__name__)

# 创建路由器, URL前缀在这里定义
router = APIRouter(prefix="/ws")

# 通过依赖注入创建和使用 WebSocketService
# 这确保了 websocket_service 能获取到全局唯一的 task_manager
websocket_service = WebSocketService(task_manager)

# ==================== WebSocket 端点 ====================

@router.websocket("/tasks/{user_id}")
async def task_status_websocket(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...)
):
    """
    任务状态WebSocket端点
    - 路径: /api/v1/ws/tasks/{user_id}?token=YOUR_JWT_TOKEN
    - 功能: 建立连接后，将实时推送该用户的所有任务状态更新。
    """
    # 先接受WebSocket连接
    await websocket.accept()
    logger.info(f"WebSocket连接已接受，开始认证: user_id={user_id}")
    
    # 然后验证用户身份
    try:
        user = await get_current_user_websocket(token=token)
        if not user or user.id != user_id:
            logger.warning(f"WebSocket 认证失败: token无效或用户不匹配. "
                           f"请求的 user_id={user_id}, token中的 user_id={user.id if user else 'N/A'}")
            # 发送认证失败消息然后关闭连接
            await websocket.send_text(json.dumps({
                "type": "authentication_failed",
                "message": "认证失败，用户不匹配或token无效",
                "timestamp": datetime.now().isoformat()
            }))
            await websocket.close(code=1008, reason="Authentication failed")
            return
    except Exception as e:
        logger.error(f"WebSocket 认证过程中发生异常: {e}", exc_info=True)
        # 发送认证错误消息然后关闭连接
        try:
            await websocket.send_text(json.dumps({
                "type": "authentication_error",
                "message": f"认证过程异常: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }))
        except:
            pass
        await websocket.close(code=1011, reason="Authentication error")
        return
    
    logger.info(f"WebSocket认证成功，建立连接: user_id={user_id}, username={user.username}")
    
    # 接受连接并处理
    await websocket_service.handle_task_status_connection(websocket, user_id)

# ==================== HTTP 端点 (用于调试和管理) ====================

@router.get("/status", summary="获取WebSocket连接状态")
async def get_websocket_status(token: str = Query(...)):
    """获取当前所有WebSocket连接的统计信息。"""
    # 验证token
    try:
        user = await get_current_user_websocket(token=token)
        if not user:
            raise HTTPException(status_code=401, detail="认证失败")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败: {str(e)}")
    
    try:
        stats = websocket_service.get_stats()
        return {
            "success": True,
            "data": stats,
            "message": "WebSocket状态获取成功"
        }
    except Exception as e:
        logger.error(f"获取WebSocket状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取WebSocket状态失败: {e}")

@router.post("/push/test-message/{user_id}", summary="推送测试消息")
async def push_test_message(
    user_id: int,
    token: str = Query(...)
):
    """向指定用户推送一条测试消息，用于验证连接。"""
    # 验证token
    try:
        user = await get_current_user_websocket(token=token)
        if not user:
            raise HTTPException(status_code=401, detail="认证失败")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败: {str(e)}")

    try:
        test_task_data = {
            "task_id": "test_task_12345",
            "name": "这是一个测试任务",
            "status": "PROCESSING",
            "stage": "TESTING",
            "progress": 50,
            "message": "如果您看到此消息，说明WebSocket连接正常。",
            "details": "这条消息由管理员手动触发。",
            "timestamp": datetime.now().isoformat()
        }
        await task_manager.push_update_to_user(user_id, test_task_data)
        return {"success": True, "message": f"测试消息已推送给用户: {user_id}"}
    except Exception as e:
        logger.error(f"推送测试消息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"推送测试消息失败: {e}")

# ==================== 路由注册 ====================

# 输出路由注册日志
logger.info("🔄 WebSocket路由重构完成，统一到 /api/v1/ws/ 前缀:")
logger.info("  - /api/v1/ws/tasks/{user_id}")
logger.info("  - /api/v1/ws/status [HTTP]")
logger.info("  - /api/v1/ws/push/test-message/{user_id} [HTTP]") 