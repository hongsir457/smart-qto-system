"""
WebSocket 连接池管理器
提供统一的 WebSocket 连接管理、心跳保活、消息分发等功能
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionMetadata:
    """连接元数据"""
    connection_id: str
    user_id: int
    websocket: WebSocket
    connected_at: datetime
    last_activity: datetime
    state: ConnectionState
    endpoint: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    ping_count: int = 0
    pong_count: int = 0
    message_count: int = 0
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，排除不能序列化的字段"""
        data = asdict(self)
        data.pop('websocket', None)
        data['connected_at'] = self.connected_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['state'] = self.state.value
        return data


class WebSocketManager:
    """
    WebSocket 连接池管理器
    提供统一的连接管理、心跳保活、消息分发等功能
    """
    
    def __init__(self, 
                 heartbeat_interval: int = 30,
                 heartbeat_timeout: int = 60,
                 max_connections_per_user: int = 5,
                 cleanup_interval: int = 300):
        """
        初始化 WebSocket 管理器
        
        Args:
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_timeout: 心跳超时时间（秒）
            max_connections_per_user: 每用户最大连接数
            cleanup_interval: 清理间隔（秒）
        """
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_connections_per_user = max_connections_per_user
        self.cleanup_interval = cleanup_interval
        
        # 连接池存储
        self.connections: Dict[str, ConnectionMetadata] = {}
        self.user_connections: Dict[int, Set[str]] = defaultdict(set)
        self.endpoint_connections: Dict[str, Set[str]] = defaultdict(set)
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        self.broadcast_handlers: List[Callable] = []
        
        # 控制标志
        self._running = False
        self._heartbeat_task = None
        self._cleanup_task = None
        self._start_time = datetime.now()
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages': 0,
            'heartbeat_sent': 0,
            'heartbeat_received': 0,
            'connections_dropped': 0,
            'errors': 0
        }
        
        logger.info("WebSocket Manager 初始化完成")
    
    async def start(self):
        """启动 WebSocket 管理器"""
        if self._running:
            logger.warning("WebSocket Manager 已经在运行")
            return
            
        self._running = True
        self._start_time = datetime.now()
        
        # 启动心跳任务
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("WebSocket Manager 已启动")
    
    async def stop(self):
        """停止 WebSocket 管理器"""
        self._running = False
        
        # 取消后台任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # 断开所有连接
        await self._disconnect_all()
        
        logger.info("WebSocket Manager 已停止")
    
    async def register_connection(self, 
                                websocket: WebSocket, 
                                user_id: int, 
                                endpoint: str,
                                metadata: Optional[Dict] = None) -> str:
        """
        注册新的 WebSocket 连接
        
        Args:
            websocket: WebSocket 实例
            user_id: 用户ID
            endpoint: 端点名称
            metadata: 额外的元数据
            
        Returns:
            连接ID
        """
        # 检查用户连接数限制
        if len(self.user_connections[user_id]) >= self.max_connections_per_user:
            oldest_connection_id = min(
                self.user_connections[user_id],
                key=lambda cid: self.connections[cid].connected_at
            )
            await self._force_disconnect(oldest_connection_id, "超出最大连接数限制")
        
        # 生成连接ID
        connection_id = f"{user_id}_{endpoint}_{uuid.uuid4().hex[:8]}"
        
        # 创建连接元数据
        now = datetime.now()
        connection_metadata = ConnectionMetadata(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=now,
            last_activity=now,
            state=ConnectionState.CONNECTED,
            endpoint=endpoint,
            ip_address=getattr(websocket.client, 'host', None) if websocket.client else None
        )
        
        # 应用额外的元数据
        if metadata:
            for key, value in metadata.items():
                if hasattr(connection_metadata, key):
                    setattr(connection_metadata, key, value)
        
        # 存储连接
        self.connections[connection_id] = connection_metadata
        self.user_connections[user_id].add(connection_id)
        self.endpoint_connections[endpoint].add(connection_id)
        
        # 更新统计
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.connections)
        
        # 发送连接确认消息
        await self._send_connection_established(connection_id)
        
        logger.info(f"WebSocket 连接已注册: {connection_id} (用户: {user_id}, 端点: {endpoint})")
        return connection_id
    
    async def unregister_connection(self, connection_id: str):
        """注销 WebSocket 连接"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        user_id = connection.user_id
        endpoint = connection.endpoint
        
        # 从所有映射中移除
        del self.connections[connection_id]
        self.user_connections[user_id].discard(connection_id)
        self.endpoint_connections[endpoint].discard(connection_id)
        
        # 清理空的集合
        if not self.user_connections[user_id]:
            del self.user_connections[user_id]
        if not self.endpoint_connections[endpoint]:
            del self.endpoint_connections[endpoint]
        
        # 更新统计
        self.stats['active_connections'] = len(self.connections)
        
        logger.info(f"WebSocket 连接已注销: {connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        向指定连接发送消息
        
        Args:
            connection_id: 连接ID
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            await connection.websocket.send_text(message_json)
            
            # 更新统计和活动时间
            connection.last_activity = datetime.now()
            connection.message_count += 1
            self.stats['total_messages'] += 1
            
            return True
            
        except Exception as e:
            logger.warning(f"向连接 {connection_id} 发送消息失败: {e}")
            connection.error_count += 1
            self.stats['errors'] += 1
            await self._mark_connection_error(connection_id)
            return False
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> int:
        """
        向用户的所有连接发送消息
        
        Args:
            user_id: 用户ID
            message: 消息内容
            
        Returns:
            成功发送的连接数
        """
        if user_id not in self.user_connections:
            return 0
        
        success_count = 0
        connection_ids = list(self.user_connections[user_id])  # 创建副本避免并发修改
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1
        
        return success_count
    
    async def send_to_endpoint(self, endpoint: str, message: Dict[str, Any]) -> int:
        """
        向指定端点的所有连接发送消息
        
        Args:
            endpoint: 端点名称
            message: 消息内容
            
        Returns:
            成功发送的连接数
        """
        if endpoint not in self.endpoint_connections:
            return 0
        
        success_count = 0
        connection_ids = list(self.endpoint_connections[endpoint])  # 创建副本
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1
        
        return success_count
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        向所有连接广播消息
        
        Args:
            message: 消息内容
            
        Returns:
            成功发送的连接数
        """
        success_count = 0
        connection_ids = list(self.connections.keys())  # 创建副本
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                success_count += 1
        
        return success_count
    
    async def handle_message(self, connection_id: str, message_data: str):
        """
        处理来自客户端的消息
        
        Args:
            connection_id: 连接ID
            message_data: 消息数据
        """
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        connection.last_activity = datetime.now()
        
        try:
            message = json.loads(message_data)
            message_type = message.get('type', 'unknown')
            
            # 处理内置消息类型
            if message_type == 'ping':
                await self._handle_ping(connection_id, message)
            elif message_type == 'pong':
                await self._handle_pong(connection_id, message)
            else:
                # 调用注册的消息处理器
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](connection_id, message)
                else:
                    logger.debug(f"未处理的消息类型: {message_type}")
        
        except json.JSONDecodeError:
            logger.warning(f"无法解析消息: {connection_id}, {message_data}")
            connection.error_count += 1
        except Exception as e:
            logger.error(f"处理消息失败: {connection_id}, {e}")
            connection.error_count += 1
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"已注册消息处理器: {message_type}")
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        if connection_id in self.connections:
            return self.connections[connection_id].to_dict()
        return None
    
    def get_user_connections(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有连接信息"""
        if user_id not in self.user_connections:
            return []
        
        return [
            self.connections[cid].to_dict() 
            for cid in self.user_connections[user_id]
            if cid in self.connections
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        now = datetime.now()
        
        # 计算实时统计
        healthy_connections = 0
        inactive_connections = 0
        
        for connection in self.connections.values():
            if connection.state == ConnectionState.CONNECTED:
                if (now - connection.last_activity).seconds < self.heartbeat_timeout:
                    healthy_connections += 1
                else:
                    inactive_connections += 1
        
        return {
            **self.stats,
            'healthy_connections': healthy_connections,
            'inactive_connections': inactive_connections,
            'users_online': len(self.user_connections),
            'endpoints_active': len(self.endpoint_connections),
            'uptime_seconds': int((now - self._start_time).total_seconds())
        }
    
    # 私有方法
    async def _heartbeat_loop(self):
        """心跳循环"""
        logger.info("心跳循环已启动")
        
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._send_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环异常: {e}")
        
        logger.info("心跳循环已停止")
    
    async def _cleanup_loop(self):
        """清理循环"""
        logger.info("清理循环已启动")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_inactive_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理循环异常: {e}")
        
        logger.info("清理循环已停止")
    
    async def _send_heartbeats(self):
        """发送心跳给所有连接"""
        now = datetime.now()
        heartbeat_message = {
            'type': 'heartbeat',
            'timestamp': now.isoformat(),
            'server_time': int(now.timestamp())
        }
        
        inactive_connections = []
        
        for connection_id, connection in self.connections.items():
            if connection.state != ConnectionState.CONNECTED:
                continue
            
            # 检查是否超时
            if (now - connection.last_activity).seconds > self.heartbeat_timeout:
                inactive_connections.append(connection_id)
                continue
            
            # 发送心跳
            if await self.send_to_connection(connection_id, heartbeat_message):
                connection.ping_count += 1
                self.stats['heartbeat_sent'] += 1
        
        # 清理超时连接
        for connection_id in inactive_connections:
            await self._force_disconnect(connection_id, "心跳超时")
    
    async def _cleanup_inactive_connections(self):
        """清理非活跃连接"""
        now = datetime.now()
        to_remove = []
        
        for connection_id, connection in self.connections.items():
            # 检查连接状态
            if connection.state in [ConnectionState.DISCONNECTED, ConnectionState.ERROR]:
                to_remove.append(connection_id)
                continue
            
            # 检查WebSocket状态
            try:
                if hasattr(connection.websocket, 'client_state'):
                    if connection.websocket.client_state.name != 'CONNECTED':
                        to_remove.append(connection_id)
            except:
                to_remove.append(connection_id)
        
        # 清理标记的连接
        for connection_id in to_remove:
            await self.unregister_connection(connection_id)
            self.stats['connections_dropped'] += 1
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个非活跃连接")
    
    async def _send_connection_established(self, connection_id: str):
        """发送连接建立消息"""
        message = {
            'type': 'connection_established',
            'connection_id': connection_id,
            'timestamp': datetime.now().isoformat(),
            'message': 'WebSocket连接已建立'
        }
        await self.send_to_connection(connection_id, message)
    
    async def _handle_ping(self, connection_id: str, message: Dict[str, Any]):
        """处理客户端ping消息"""
        pong_message = {
            'type': 'pong',
            'timestamp': datetime.now().isoformat(),
            'ping_timestamp': message.get('timestamp')
        }
        await self.send_to_connection(connection_id, pong_message)
        self.stats['heartbeat_received'] += 1
    
    async def _handle_pong(self, connection_id: str, message: Dict[str, Any]):
        """处理客户端pong消息"""
        if connection_id in self.connections:
            self.connections[connection_id].pong_count += 1
    
    async def _mark_connection_error(self, connection_id: str):
        """标记连接为错误状态"""
        if connection_id in self.connections:
            self.connections[connection_id].state = ConnectionState.ERROR
    
    async def _force_disconnect(self, connection_id: str, reason: str):
        """强制断开连接"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        connection.state = ConnectionState.DISCONNECTING
        
        try:
            # 发送断开通知
            await connection.websocket.send_text(json.dumps({
                'type': 'disconnect',
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }))
            
            # 关闭连接
            await connection.websocket.close()
        except:
            pass  # 忽略关闭时的错误
        
        await self.unregister_connection(connection_id)
        logger.info(f"强制断开连接: {connection_id}, 原因: {reason}")
    
    async def _disconnect_all(self):
        """断开所有连接"""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self._force_disconnect(connection_id, "服务器关闭")


# 全局 WebSocket 管理器实例
websocket_manager = WebSocketManager() 