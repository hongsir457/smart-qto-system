"""
WebSocket服务
提供WebSocket连接管理、消息广播、用户隔离等功能
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any, Set
import json
import logging
import asyncio
import threading
from datetime import datetime
from ..models.user import User
from ..tasks import RealTimeTaskManager  # 导入 RealTimeTaskManager

logger = logging.getLogger(__name__)

class WebSocketService:
    """WebSocket业务服务，由RealTimeTaskManager驱动"""
    
    def __init__(self, task_manager: RealTimeTaskManager):
        # 依赖注入，使用全局唯一的 task_manager
        self.task_manager = task_manager
        self._pubsub_thread = None
        self._pubsub_active = False
        
        # 启动Redis PubSub监听器
        self._start_pubsub_listener()
    
    def _start_pubsub_listener(self):
        """启动Redis PubSub监听器来接收任务更新"""
        if self._pubsub_thread is None or not self._pubsub_thread.is_alive():
            self._pubsub_active = True
            self._pubsub_thread = threading.Thread(target=self._pubsub_listener, daemon=True)
            self._pubsub_thread.start()
            logger.info("Redis PubSub监听器已启动")
    
    def _pubsub_listener(self):
        """Redis PubSub监听器，接收任务更新并推送到WebSocket"""
        try:
            pubsub = self.task_manager.redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe("task_updates")
            logger.info("WebSocket服务订阅了Redis task_updates频道")

            while self._pubsub_active:
                try:
                    # 使用较短的超时来避免阻塞
                    message = pubsub.get_message(timeout=1.0)
                    if message is None:
                        continue
                        
                    if message["type"] != "message":
                        continue
                        
                    # 解析Redis消息
                    raw = message["data"]
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    
                    data = json.loads(raw)
                    logger.debug(f"收到Redis任务更新: {data.get('type')} - {data.get('task_id')}")
                    
                    # 异步推送到WebSocket
                    asyncio.run(self._handle_redis_task_update(data))
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"解析Redis消息失败: {e}")
                except Exception as e:
                    logger.error(f"处理Redis消息失败: {e}")
                    
        except Exception as e:
            logger.error(f"Redis PubSub监听器异常: {e}")
        finally:
            logger.info("Redis PubSub监听器已停止")
    
    async def _handle_redis_task_update(self, data: Dict):
        """处理来自Redis的任务更新消息，并推送到相应的WebSocket连接"""
        try:
            task_id = data.get("task_id")
            user_id = data.get("user_id")
            message_type = data.get("type")
            
            if not task_id:
                logger.warning("Redis消息缺少task_id")
                return
            
            # 获取该任务所属的用户ID（如果消息中没有）
            if not user_id:
                task = self.task_manager.get_task(task_id)
                if task:
                    user_id = task.user_id
                else:
                    logger.warning(f"无法找到任务 {task_id} 的用户ID")
                    return
            
            # 获取该用户的WebSocket连接
            user_websockets = self.task_manager.user_connections.get(user_id, set())
            if not user_websockets:
                logger.debug(f"用户 {user_id} 没有活跃的WebSocket连接")
                return
            
            # 格式化消息以匹配前端期望的格式
            if message_type == "task_update":
                # 任务状态更新消息
                websocket_message = {
                    "type": "task_update",
                    "task_id": task_id,
                    "data": data.get("data", {}),
                    "timestamp": data.get("timestamp")
                }
            elif message_type == "task_message":
                # 任务详细消息
                websocket_message = {
                    "type": "task_message",
                    "task_id": task_id,
                    "task_name": data.get("task_name"),
                    "message": data.get("message"),
                    "stage": data.get("stage"),
                    "progress": data.get("progress"),
                    "status": data.get("status"),
                    "timestamp": data.get("timestamp"),
                    "user_id": user_id
                }
            else:
                # 未知消息类型，直接转发
                websocket_message = data
            
            # 推送到用户的所有WebSocket连接
            message_json = json.dumps(websocket_message, ensure_ascii=False)
            disconnected_websockets = set()
            
            for websocket in user_websockets.copy():
                try:
                    await websocket.send_text(message_json)
                    logger.debug(f"消息已推送到用户 {user_id} 的WebSocket连接")
                except ConnectionResetError:
                    logger.debug(f"WebSocket连接已重置: user={user_id}")
                    disconnected_websockets.add(websocket)
                except BrokenPipeError:
                    logger.debug(f"WebSocket管道已断开: user={user_id}")
                    disconnected_websockets.add(websocket)
                except Exception as e:
                    logger.warning(f"推送消息到WebSocket失败: user={user_id}, error={e}")
                    disconnected_websockets.add(websocket)
            
            # 清理断开的连接
            if disconnected_websockets:
                user_websockets -= disconnected_websockets
                logger.debug(f"清理了 {len(disconnected_websockets)} 个断开的WebSocket连接")
                    
        except Exception as e:
            logger.error(f"处理Redis任务更新失败: {e}")
    
    async def handle_task_status_connection(self, websocket: WebSocket, user_id: int):
        """处理任务状态WebSocket连接，并监听该用户的所有任务更新"""
        await self.task_manager.register_user_websocket(user_id, websocket)
        
        try:
            # 发送初始的欢迎消息，不自动加载历史任务
            await self.send_initial_messages(user_id, websocket, load_history=False)

            while True:
                # 这个循环现在主要用于保持连接活跃
                # 真正的消息推送由Redis PubSub监听器处理
                try:
                    # 设置较长的超时，避免频繁ping导致连接不稳定
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                    # 如果收到消息，可以进行处理
                    await self._handle_client_message(user_id, websocket, message)
                except asyncio.TimeoutError:
                    # 超时时发送心跳，但捕获可能的异常
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "heartbeat",
                            "timestamp": datetime.now().isoformat()
                        }))
                        logger.debug(f"发送心跳到用户 {user_id}")
                    except Exception as ping_error:
                        logger.warning(f"心跳发送失败，用户 {user_id} 可能已断开: {ping_error}")
                        break
                except WebSocketDisconnect:
                    logger.info(f"WebSocket 正常断开: user={user_id}")
                    break
                except Exception as e:
                    # 捕获所有其他异常，包括连接中断
                    logger.warning(f"WebSocket连接异常: user={user_id}, error={e}")
                    break
                
        except Exception as e:
            logger.error(f"任务状态 WebSocket 处理失败: user={user_id}, error={e}", exc_info=True)
        finally:
            logger.info(f"清理WebSocket连接: user={user_id}")
            # 安全地清理连接
            try:
                self.task_manager.unregister_websocket(websocket)
            except Exception as cleanup_error:
                logger.warning(f"清理WebSocket连接时出错: {cleanup_error}")
            
    async def send_initial_messages(self, user_id: int, websocket: WebSocket, load_history: bool = False):
        """发送连接成功消息，可选择是否加载历史任务。优雅处理连接断开的情况。"""
        try:
            # 1. 发送连接成功消息
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "message": "WebSocket连接已建立，开始接收实时任务消息",
                "timestamp": datetime.now().isoformat(),
                "load_history": load_history
            }))

            # 2. 根据参数决定是否发送历史任务
            if load_history:
                tasks = self.task_manager.get_user_tasks(user_id)
                if tasks:
                    await websocket.send_text(json.dumps({
                        "type": "user_tasks",
                        "tasks": [task.to_dict() for task in tasks],
                        "message": f"已加载 {len(tasks)} 个历史任务状态"
                    }))
                    logger.info(f"已向用户 {user_id} 发送 {len(tasks)} 个历史任务")
                else:
                    logger.info(f"用户 {user_id} 没有历史任务")
            else:
                logger.info(f"用户 {user_id} 连接建立，跳过历史任务加载")
                
        except (WebSocketDisconnect, ConnectionResetError) as e:
            # 这些是预期的断开，记录为INFO
            logger.info(f"客户端在发送初始消息期间断开连接 (预期行为): user={user_id}, error={type(e).__name__}")
        except Exception as e:
            # 捕获其他潜在的发送错误，但记录为WARNING，而不是ERROR
            # 特别是 websockets.exceptions.ConnectionClosedError
            logger.warning(
                f"发送初始消息时发生非致命错误: user={user_id}, error_type={type(e).__name__}, error={e}"
            )

    async def _handle_client_message(self, user_id: int, websocket: WebSocket, data: str):
        """处理来自客户端的消息"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            logger.debug(f"收到客户端消息: user={user_id}, type={message_type}")
            
            if message_type == "get_user_tasks":
                # 客户端请求获取任务列表
                tasks = self.task_manager.get_user_tasks(user_id)
                await websocket.send_text(json.dumps({
                    "type": "user_tasks",
                    "tasks": [task.to_dict() for task in tasks],
                    "message": f"当前有 {len(tasks)} 个任务"
                }))
            elif message_type == "load_history_tasks":
                # 客户端主动请求加载历史任务
                tasks = self.task_manager.get_user_tasks(user_id)
                if tasks:
                    await websocket.send_text(json.dumps({
                        "type": "user_tasks",
                        "tasks": [task.to_dict() for task in tasks],
                        "message": f"已加载 {len(tasks)} 个历史任务状态",
                        "requested": True  # 标记这是用户主动请求的
                    }))
                    logger.info(f"用户 {user_id} 主动请求加载 {len(tasks)} 个历史任务")
                else:
                    await websocket.send_text(json.dumps({
                        "type": "user_tasks",
                        "tasks": [],
                        "message": "暂无历史任务",
                        "requested": True
                    }))
                    logger.info(f"用户 {user_id} 请求历史任务，但没有找到任务")
            elif message_type == "clear_tasks":
                # 客户端请求清空任务显示（不发送历史任务）
                await websocket.send_text(json.dumps({
                    "type": "tasks_cleared",
                    "message": "任务列表已清空",
                    "timestamp": datetime.now().isoformat()
                }))
                logger.info(f"用户 {user_id} 清空了任务列表")
            elif message_type == "ping":
                # 客户端ping，回复pong
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            else:
                logger.debug(f"未处理的客户端消息类型: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"无法解析客户端消息: user={user_id}, data={data}")
        except Exception as e:
            logger.error(f"处理客户端消息失败: user={user_id}, error={e}", exc_info=True)

    def get_stats(self) -> Dict[str, Any]:
        """获取WebSocket连接统计信息"""
        try:
            task_stats = self.task_manager.get_task_statistics()
            active_tasks = self.task_manager.get_active_tasks()
            
            return {
                "task_statistics": task_stats,
                "active_tasks_count": len(active_tasks),
                "user_connections_count": len(self.task_manager.user_connections),
                "websocket_connections_count": len(self.task_manager.websocket_connections),
                "pubsub_active": self._pubsub_active,
                "message": "WebSocket服务运行正常"
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}", exc_info=True)
            return {
                "error": f"获取统计信息失败: {e}",
                "message": "WebSocket服务状态未知"
            }
    
    def stop(self):
        """停止WebSocket服务"""
        self._pubsub_active = False
        if self._pubsub_thread and self._pubsub_thread.is_alive():
            self._pubsub_thread.join(timeout=5.0)
            logger.info("WebSocket服务已停止")

# 创建一个由全局 task_manager 驱动的 websocket_service 单例
# 但更好的做法是在 FastAPI 的依赖注入系统中处理
# 这里我们先不创建全局实例，而是在使用它的地方创建

# 移除旧的 ConnectionManager 和依赖它的 WebSocketService 实现
# ... 