from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
import asyncio
import logging
from app.api import deps
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# 存储WebSocket连接的管理器
class ConnectionManager:
    def __init__(self):
        # 存储活跃连接：{user_id: {connection_id: websocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        # 存储任务订阅：{task_id: [user_ids]}
        self.task_subscriptions: Dict[str, List[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, connection_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        logger.info(f"用户 {user_id} 建立WebSocket连接: {connection_id}")

    def disconnect(self, user_id: int, connection_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]
                logger.info(f"用户 {user_id} 断开WebSocket连接: {connection_id}")
            
            # 如果用户没有其他连接，删除用户记录
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        """向特定用户发送消息"""
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for connection_id, websocket in self.active_connections[user_id].items():
                try:
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    logger.warning(f"向用户 {user_id} 连接 {connection_id} 发送消息失败: {e}")
                    disconnected_connections.append(connection_id)
            
            # 清理断开的连接
            for connection_id in disconnected_connections:
                self.disconnect(user_id, connection_id)

    async def send_task_progress(self, task_id: str, progress_data: dict):
        """向订阅特定任务的用户发送进度更新"""
        if task_id in self.task_subscriptions:
            message = {
                "type": "task_progress",
                "task_id": task_id,
                "data": progress_data
            }
            
            for user_id in self.task_subscriptions[task_id]:
                await self.send_personal_message(message, user_id)

    def subscribe_task(self, task_id: str, user_id: int):
        """订阅任务进度"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = []
        
        if user_id not in self.task_subscriptions[task_id]:
            self.task_subscriptions[task_id].append(user_id)
            logger.info(f"用户 {user_id} 订阅任务 {task_id}")

    def unsubscribe_task(self, task_id: str, user_id: int):
        """取消订阅任务进度"""
        if task_id in self.task_subscriptions:
            if user_id in self.task_subscriptions[task_id]:
                self.task_subscriptions[task_id].remove(user_id)
                logger.info(f"用户 {user_id} 取消订阅任务 {task_id}")
            
            # 如果没有用户订阅，删除任务记录
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]

# 全局连接管理器实例
manager = ConnectionManager()

@router.websocket("/ws/{connection_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    connection_id: str
):
    """WebSocket连接端点"""
    try:
        # 暂时跳过token验证，使用固定用户ID进行测试
        user_id = 1  # 测试用户ID
        
        # 建立连接
        await manager.connect(websocket, user_id, connection_id)
        
        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "WebSocket连接已建立",
            "connection_id": connection_id,
            "user_id": user_id
        }, ensure_ascii=False))
        
        # 保持连接并处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理不同类型的消息
                if message.get("type") == "subscribe_task" or message.get("action") == "subscribe":
                    task_id = message.get("task_id")
                    if task_id:
                        manager.subscribe_task(task_id, user_id)
                        await websocket.send_text(json.dumps({
                            "type": "subscription_confirmed",
                            "task_id": task_id,
                            "message": f"已订阅任务 {task_id} 的进度更新"
                        }, ensure_ascii=False))
                
                elif message.get("type") == "unsubscribe_task" or message.get("action") == "unsubscribe":
                    task_id = message.get("task_id")
                    if task_id:
                        manager.unsubscribe_task(task_id, user_id)
                        await websocket.send_text(json.dumps({
                            "type": "unsubscription_confirmed",
                            "task_id": task_id,
                            "message": f"已取消订阅任务 {task_id}"
                        }, ensure_ascii=False))
                
                elif message.get("type") == "ping":
                    # 心跳检测
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }, ensure_ascii=False))
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "无效的JSON格式"
                }, ensure_ascii=False))
            except Exception as e:
                logger.error(f"处理WebSocket消息时发生错误: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"处理消息时发生错误: {str(e)}"
                }, ensure_ascii=False))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket连接发生错误: {e}")
    finally:
        # 清理连接
        manager.disconnect(user_id, connection_id)

# 提供给其他模块使用的进度推送函数
async def push_task_progress(task_id: str, progress_data: dict):
    """推送任务进度更新"""
    await manager.send_task_progress(task_id, progress_data)

async def push_user_notification(user_id: int, notification: dict):
    """推送用户通知"""
    message = {
        "type": "notification",
        "data": notification
    }
    await manager.send_personal_message(message, user_id) 