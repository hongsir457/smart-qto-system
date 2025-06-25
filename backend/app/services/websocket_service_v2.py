"""
WebSocket 服务 V2
基于 WebSocketManager 连接池的新版本服务
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from app.core.websocket_manager import websocket_manager, ConnectionState
from app.tasks import RealTimeTaskManager

logger = logging.getLogger(__name__)


class WebSocketServiceV2:
    """
    基于 WebSocketManager 连接池的 WebSocket 服务
    """
    
    def __init__(self, task_manager: RealTimeTaskManager):
        self.task_manager = task_manager
        self.websocket_manager = websocket_manager
        
        # 注册消息处理器
        self._register_message_handlers()
        
        logger.info("WebSocket Service V2 初始化完成")
    
    async def start(self):
        """启动服务"""
        await self.websocket_manager.start()
        logger.info("WebSocket Service V2 已启动")
    
    async def stop(self):
        """停止服务"""
        await self.websocket_manager.stop()
        logger.info("WebSocket Service V2 已停止")
    
    def _register_message_handlers(self):
        """注册消息处理器"""
        # 注册任务相关的消息处理器
        self.websocket_manager.register_message_handler(
            'get_user_tasks', self._handle_get_user_tasks
        )
        self.websocket_manager.register_message_handler(
            'load_history_tasks', self._handle_load_history_tasks
        )
        self.websocket_manager.register_message_handler(
            'clear_tasks', self._handle_clear_tasks
        )
        self.websocket_manager.register_message_handler(
            'subscribe_task', self._handle_subscribe_task
        )
        self.websocket_manager.register_message_handler(
            'unsubscribe_task', self._handle_unsubscribe_task
        )
    
    async def handle_connection(self, websocket: WebSocket, user_id: int, endpoint: str = "default"):
        """
        处理 WebSocket 连接
        
        Args:
            websocket: WebSocket 实例
            user_id: 用户ID
            endpoint: 端点名称
        """
        connection_id = None
        try:
            # 注册连接
            connection_id = await self.websocket_manager.register_connection(
                websocket=websocket,
                user_id=user_id,
                endpoint=endpoint,
                metadata={
                    'user_agent': websocket.headers.get('user-agent'),
                }
            )
            
            logger.info(f"WebSocket 连接已建立: {connection_id}")
            
            # 发送初始消息
            await self._send_initial_messages(connection_id, user_id)
            
            # 开始消息循环
            await self._message_loop(connection_id, websocket)
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket 正常断开: user={user_id}")
        except Exception as e:
            logger.error(f"WebSocket 连接处理异常: user={user_id}, error={e}", exc_info=True)
        finally:
            # 清理连接
            if connection_id:
                await self.websocket_manager.unregister_connection(connection_id)
    
    async def _message_loop(self, connection_id: str, websocket: WebSocket):
        """消息处理循环"""
        while True:
            try:
                # 接收消息
                message = await websocket.receive_text()
                
                # 交给 WebSocketManager 处理
                await self.websocket_manager.handle_message(connection_id, message)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"消息处理异常: {connection_id}, {e}")
                break
    
    async def _send_initial_messages(self, connection_id: str, user_id: int):
        """发送初始消息"""
        try:
            # 发送欢迎消息
            await self.websocket_manager.send_to_connection(connection_id, {
                'type': 'welcome',
                'message': '欢迎使用实时任务监控系统',
                'timestamp': datetime.now().isoformat(),
                'connection_id': connection_id
            })
            
            # 发送用户任务状态
            tasks = self.task_manager.get_user_tasks(user_id)
            if tasks:
                await self.websocket_manager.send_to_connection(connection_id, {
                    'type': 'user_tasks',
                    'tasks': [task.to_dict() for task in tasks],
                    'count': len(tasks),
                    'message': f'当前有 {len(tasks)} 个任务'
                })
            
        except Exception as e:
            logger.error(f"发送初始消息失败: {connection_id}, {e}")
    
    # 消息处理器
    async def _handle_get_user_tasks(self, connection_id: str, message: Dict[str, Any]):
        """处理获取用户任务请求"""
        try:
            connection_info = self.websocket_manager.get_connection_info(connection_id)
            if not connection_info:
                return
            
            user_id = connection_info['user_id']
            tasks = self.task_manager.get_user_tasks(user_id)
            
            await self.websocket_manager.send_to_connection(connection_id, {
                'type': 'user_tasks',
                'tasks': [task.to_dict() for task in tasks],
                'count': len(tasks),
                'message': f'当前有 {len(tasks)} 个任务',
                'requested': True
            })
            
        except Exception as e:
            logger.error(f"处理用户任务请求失败: {connection_id}, {e}")
    
    async def _handle_load_history_tasks(self, connection_id: str, message: Dict[str, Any]):
        """处理加载历史任务请求"""
        try:
            connection_info = self.websocket_manager.get_connection_info(connection_id)
            if not connection_info:
                return
            
            user_id = connection_info['user_id']
            tasks = self.task_manager.get_user_tasks(user_id)
            
            await self.websocket_manager.send_to_connection(connection_id, {
                'type': 'history_tasks',
                'tasks': [task.to_dict() for task in tasks],
                'count': len(tasks),
                'message': f'已加载 {len(tasks)} 个历史任务',
                'requested': True
            })
            
        except Exception as e:
            logger.error(f"处理历史任务请求失败: {connection_id}, {e}")
    
    async def _handle_clear_tasks(self, connection_id: str, message: Dict[str, Any]):
        """处理清空任务请求"""
        try:
            await self.websocket_manager.send_to_connection(connection_id, {
                'type': 'tasks_cleared',
                'message': '任务列表已清空',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"处理清空任务请求失败: {connection_id}, {e}")
    
    async def _handle_subscribe_task(self, connection_id: str, message: Dict[str, Any]):
        """处理任务订阅请求"""
        try:
            task_id = message.get('task_id')
            if not task_id:
                await self.websocket_manager.send_to_connection(connection_id, {
                    'type': 'error',
                    'message': '缺少任务ID',
                    'timestamp': datetime.now().isoformat()
                })
                return
            
            # 这里可以添加任务订阅逻辑
            await self.websocket_manager.send_to_connection(connection_id, {
                'type': 'subscription_confirmed',
                'task_id': task_id,
                'message': f'已订阅任务 {task_id}',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"处理任务订阅请求失败: {connection_id}, {e}")
    
    async def _handle_unsubscribe_task(self, connection_id: str, message: Dict[str, Any]):
        """处理取消任务订阅请求"""
        try:
            task_id = message.get('task_id')
            if not task_id:
                return
            
            await self.websocket_manager.send_to_connection(connection_id, {
                'type': 'unsubscription_confirmed',
                'task_id': task_id,
                'message': f'已取消订阅任务 {task_id}',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"处理取消任务订阅请求失败: {connection_id}, {e}")
    
    # 公共接口方法
    async def notify_user(self, user_id: int, message: Dict[str, Any]) -> int:
        """
        通知指定用户
        
        Args:
            user_id: 用户ID
            message: 消息内容
            
        Returns:
            成功发送的连接数
        """
        return await self.websocket_manager.send_to_user(user_id, message)
    
    async def notify_endpoint(self, endpoint: str, message: Dict[str, Any]) -> int:
        """
        通知指定端点的所有连接
        
        Args:
            endpoint: 端点名称
            message: 消息内容
            
        Returns:
            成功发送的连接数
        """
        return await self.websocket_manager.send_to_endpoint(endpoint, message)
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        广播消息给所有连接
        
        Args:
            message: 消息内容
            
        Returns:
            成功发送的连接数
        """
        return await self.websocket_manager.broadcast(message)
    
    async def notify_task_update(self, user_id: int, task_data: Dict[str, Any]):
        """
        通知任务更新
        
        Args:
            user_id: 用户ID
            task_data: 任务数据
        """
        message = {
            'type': 'task_update',
            'task_id': task_data.get('task_id'),
            'status': task_data.get('status'),
            'stage': task_data.get('stage'),
            'progress': task_data.get('progress'),
            'message': task_data.get('message'),
            'timestamp': task_data.get('timestamp', datetime.now().isoformat()),
            'data': task_data
        }
        
        return await self.notify_user(user_id, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        manager_stats = self.websocket_manager.get_stats()
        
        return {
            'websocket_manager': manager_stats,
            'service_version': 'v2',
            'features': [
                'connection_pool',
                'heartbeat_management',
                'auto_cleanup',
                'message_routing',
                'user_isolation'
            ]
        }
    
    def get_user_connections_info(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户连接信息"""
        return self.websocket_manager.get_user_connections(user_id)


# 创建全局服务实例（需要在应用启动时初始化）
websocket_service_v2: Optional[WebSocketServiceV2] = None


def get_websocket_service_v2() -> WebSocketServiceV2:
    """获取 WebSocket 服务实例"""
    global websocket_service_v2
    if websocket_service_v2 is None:
        from app.tasks import task_manager
        websocket_service_v2 = WebSocketServiceV2(task_manager)
    return websocket_service_v2 