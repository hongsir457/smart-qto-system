# -*- coding: utf-8 -*-
"""
实时任务管理器
负责管理所有任务的状态、进度和WebSocket连接
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict
import weakref
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    STARTED = "started"      # 已开始
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"      # 成功完成
    FAILURE = "failure"      # 失败
    RETRY = "retry"          # 重试中
    REVOKED = "revoked"      # 已撤销

class TaskStage(Enum):
    """任务阶段枚举"""
    QUEUED = "queued"               # 排队中
    UPLOADING = "uploading"         # 上传中
    INITIALIZING = "initializing"   # 初始化
    FILE_PROCESSING = "file_processing"  # 文件处理
    OCR_RECOGNITION = "ocr_recognition"  # OCR识别
    OCR_PROCESSING = "ocr_processing"  # OCR处理中
    COMPONENT_DETECTION = "component_detection"  # 构件检测
    GPT_ANALYSIS = "gpt_analysis"   # GPT分析
    QUANTITY_CALCULATION = "quantity_calculation"  # 工程量计算
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"              # 失败

class TaskInfo:
    """任务信息类"""
    def __init__(self, task_id: str, name: str, user_id: int = None):
        self.task_id = task_id
        self.name = name
        self.user_id = user_id
        self.status = TaskStatus.PENDING
        self.stage = TaskStage.QUEUED
        self.progress = 0
        self.message = "任务已创建"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.results: Optional[Dict] = None
        self.metadata: Dict = {}

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "user_id": self.user_id,
            "status": self.status.value,
            "stage": self.stage.value,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "results": self.results,
            "metadata": self.metadata,
            "duration": self._calculate_duration()
        }

    def _calculate_duration(self) -> Optional[float]:
        """计算任务持续时间（秒）"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

class RealTimeTaskManager:
    """实时任务管理器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.tasks: Dict[str, TaskInfo] = {}
        self.websocket_connections: Dict[str, Set[Any]] = {}  # task_id -> websockets
        self.user_connections: Dict[int, Set[Any]] = {}  # user_id -> websockets
        self._cleanup_interval = 3600  # 1小时清理一次过期任务
        
        # 启动时自动清理旧的drawing_analysis任务
        try:
            self._cleanup_drawing_analysis_tasks()
        except Exception as e:
            logger.warning(f"启动时清理drawing_analysis任务失败: {e}")
        
        # 启动Redis订阅线程（仅在主进程/UVicorn中发挥作用）
        try:
            import os
            if os.getenv("RUN_MAIN") == "true" or os.getenv("USE_PUBSUB_LISTENER", "1") == "1":
                threading.Thread(target=self._pubsub_listener, daemon=True).start()
        except Exception as e:
            logger.warning(f"启动任务PubSub监听失败: {e}")
        
    def _cleanup_drawing_analysis_tasks(self):
        """清理Redis中的drawing_analysis任务"""
        try:
            # 从Redis中查找并删除所有drawing_analysis任务
            pattern = "task:*"
            cleaned_count = 0
            
            for key in self.redis_client.scan_iter(match=pattern, count=100):
                try:
                    data = self.redis_client.get(key)
                    if data:
                        task_dict = json.loads(data)
                        if task_dict.get("name", "").startswith("drawing_analysis:"):
                            self.redis_client.delete(key)
                            cleaned_count += 1
                except Exception as e:
                    logger.debug(f"处理Redis键失败: {key}, {e}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"启动时清理了 {cleaned_count} 个Redis中的drawing_analysis任务")
        except Exception as e:
            logger.error(f"清理Redis drawing_analysis任务失败: {e}")
        
    def create_task(self, task_id: str = None, name: str = "Unnamed Task", user_id: int = None, metadata: Dict = None) -> str:
        """创建新任务"""
        # 如果未传入 task_id，则自动生成
        if not task_id:
            task_id = str(uuid.uuid4())

        task_info = TaskInfo(task_id, name, user_id)
        
        if metadata:
            task_info.metadata.update(metadata)
            
        self.tasks[task_id] = task_info
        
        # 保存到Redis
        self._save_task_to_redis(task_info)
        
        logger.info(f"创建新任务: {task_id} - {name}")

        # 立即通过 WebSocket 回调推送任务创建事件
        websocket_callback = getattr(self, "_websocket_push_callback", None)
        if websocket_callback:
            try:
                # 创建任务时仍标记为 pending
                self._safe_async_run(websocket_callback(task_id, task_info.to_dict()))
            except Exception as e:
                logger.error(f"创建任务时 WebSocket 推送回调失败: {e}")

        return task_id
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               stage: TaskStage = None, progress: int = None,
                               message: str = None, error_message: str = None,
                               results: Dict = None) -> bool:
        """更新任务状态"""
        if task_id not in self.tasks:
            logger.warning(f"任务不存在，自动创建: {task_id}")
            # 自动创建缺失的任务
            self.create_task(
                task_id=task_id,
                name=f"auto_created_task:{task_id[:8]}",
                user_id=None,
                metadata={"auto_created": True}
            )
        
        task = self.tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if stage is not None:
            task.stage = stage
        if progress is not None:
            task.progress = max(0, min(100, progress))
        if message is not None:
            task.message = message
        if error_message is not None:
            task.error_message = error_message
        if results is not None:
            task.results = results
            
        # 更新特殊时间戳
        if status == TaskStatus.STARTED and not task.started_at:
            task.started_at = datetime.now()
        elif status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]:
            task.completed_at = datetime.now()
        
        # 保存到Redis
        self._save_task_to_redis(task)
        
        logger.info(f"任务状态更新: {task_id} -> {status.value} ({stage.value if stage else 'N/A'}) - {progress}% - {message}")
        
        # WebSocket推送 - 使用Redis PubSub实现跨进程通信
        try:
            # 直接发布到Redis，无论是否在主进程中
            websocket_message = {
                "type": "task_update",
                "task_id": task_id,
                "data": task.to_dict(),
                "timestamp": task.updated_at.isoformat()
            }
            
            self.redis_client.publish("task_updates", json.dumps(websocket_message))
            logger.debug(f"Redis WebSocket消息已发布: {task_id}")
            
            # 发布详细的处理消息
            detail_message = {
                "type": "task_message",
                "task_id": task_id,
                "task_name": task.name,
                "message": message or f"任务状态: {status.value}",
                "stage": stage.value if stage else None,
                "progress": progress,
                "status": status.value,
                "timestamp": task.updated_at.isoformat(),
                "user_id": task.user_id
            }
            
            self.redis_client.publish("task_updates", json.dumps(detail_message))
            logger.debug(f"Redis 详细消息已发布: {task_id} - {message}")
            
        except Exception as e:
            logger.error(f"Redis WebSocket消息发布失败: {e}")
        
        # 保留原有的直接回调方式作为备用（仅在主进程中生效）
        websocket_callback = getattr(self, "_websocket_push_callback", None)
        if websocket_callback:
            try:
                # 确保异步调用
                if asyncio.iscoroutinefunction(websocket_callback):
                    self._safe_async_run(websocket_callback(task_id, task.to_dict()))
                else:
                    # 如果不是协程函数，直接调用
                    websocket_callback(task_id, task.to_dict())
                    
                logger.debug(f"直接WebSocket推送成功: {task_id}")
            except Exception as e:
                logger.debug(f"直接WebSocket推送失败(这在Celery Worker中是正常的): {e}")
        else:
            logger.debug("WebSocket推送回调未设置(这在Celery Worker中是正常的)")
        
        return True
    
    async def register_websocket(self, task_id: str, websocket: Any):
        """注册WebSocket连接到特定任务"""
        if task_id not in self.websocket_connections:
            self.websocket_connections[task_id] = set()
        
        self.websocket_connections[task_id].add(websocket)
        logger.info(f"WebSocket已注册到任务: {task_id}")
        
        # 如果任务存在，立即发送当前状态
        if task_id in self.tasks:
            await self._send_task_update(websocket, self.tasks[task_id])
    
    async def register_user_websocket(self, user_id: int, websocket: Any):
        """注册用户WebSocket连接"""
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        
        self.user_connections[user_id].add(websocket)
        logger.info(f"WebSocket已注册到用户: {user_id}")
    
    def unregister_websocket(self, websocket: Any):
        """注销WebSocket连接"""
        # 从任务连接中移除
        for task_id, connections in self.websocket_connections.items():
            connections.discard(websocket)
        
        # 从用户连接中移除
        for user_id, connections in self.user_connections.items():
            connections.discard(websocket)
        
        logger.info("WebSocket连接已注销")
    
    async def _broadcast_task_update(self, task: TaskInfo):
        """广播任务更新到WebSocket"""
        if hasattr(self, 'websocket_connections') and self.websocket_connections:
            # 发送到任务特定的WebSocket连接
            task_websockets = [ws for task_id, ws in self.websocket_connections.items() if task_id == task.task_id]
            if task_websockets:
                data = {
                    "type": "task_update",
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "stage": task.stage.value,
                    "progress": task.progress,
                    "message": task.message,
                    "error_message": task.error_message,
                    "results": task.results,
                    "timestamp": task.updated_at.isoformat(),
                    "user_id": task.user_id  # 添加用户ID
                }
                
                await self._send_to_websockets(set(task_websockets), data)
        
        # 发送到所有用户连接
        if hasattr(self, 'user_websockets') and self.user_websockets:
            user_websockets = self.user_websockets.get(task.user_id, set())
            if user_websockets:
                data = {
                    "type": "task_update",
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "stage": task.stage.value,
                    "progress": task.progress,
                    "message": task.message,
                    "error_message": task.error_message,
                    "results": task.results,
                    "timestamp": task.updated_at.isoformat(),
                    "user_id": task.user_id
                }
                
                await self._send_to_websockets(user_websockets, data)
        
        # 通知外部WebSocket管理器（如果存在）
        try:
            # 尝试导入全局WebSocket管理器
            from app.api.v1.websockets import connection_manager
            await connection_manager.send_to_user(task.user_id, {
                "type": "task_update",
                "task": task.to_dict(),
                "timestamp": task.updated_at.isoformat()
            })
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"发送任务更新到WebSocket管理器失败: {e}")

    async def _send_to_websockets(self, websockets: Set[Any], data: Dict):
        """向WebSocket连接集合发送数据"""
        if not websockets:
            return
        
        message = json.dumps(data, ensure_ascii=False)
        disconnected_websockets = set()
        
        for websocket in websockets.copy():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"WebSocket发送失败: {e}")
                disconnected_websockets.add(websocket)
        
        # 清理断开的连接
        websockets -= disconnected_websockets
    
    async def _send_task_update(self, websocket: Any, task: TaskInfo):
        """向单个WebSocket发送任务更新"""
        try:
            update_data = {
                "type": "task_update",
                "task_id": task.task_id,
                "data": task.to_dict()
            }
            await websocket.send_text(json.dumps(update_data, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"发送任务更新失败: {e}")
    
    def _save_task_to_redis(self, task: TaskInfo):
        """保存任务到Redis"""
        try:
            key = f"task:{task.task_id}"
            value = json.dumps(task.to_dict(), ensure_ascii=False)
            # 设置24小时过期
            self.redis_client.setex(key, 86400, value)

            # 发布更新消息，跨进程通知
            try:
                self.redis_client.publish("task_updates", value)
            except Exception as e:
                logger.debug(f"发布任务更新失败: {e}")
        except Exception as e:
            logger.error(f"保存任务到Redis失败: {e}")
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        if task_id in self.tasks:
            return self.tasks[task_id]
        
        # 尝试从Redis恢复
        try:
            key = f"task:{task_id}"
            data = self.redis_client.get(key)
            if data:
                task_dict = json.loads(data)
                task = self._dict_to_task_info(task_dict)
                self.tasks[task_id] = task
                return task
        except Exception as e:
            logger.error(f"从Redis恢复任务失败: {e}")
        
        return None
    
    def _dict_to_task_info(self, data: Dict) -> TaskInfo:
        """从字典恢复TaskInfo对象"""
        task = TaskInfo(data["task_id"], data["name"], data.get("user_id"))
        task.status = TaskStatus(data["status"])
        task.stage = TaskStage(data["stage"])
        task.progress = data["progress"]
        task.message = data["message"]
        task.created_at = datetime.fromisoformat(data["created_at"])
        task.updated_at = datetime.fromisoformat(data["updated_at"])
        
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        
        task.error_message = data.get("error_message")
        task.results = data.get("results")
        task.metadata = data.get("metadata", {})
        
        return task
    
    def _load_tasks_from_redis(self):
        """批量从Redis加载任务到内存（如有必要）"""
        try:
            for key in self.redis_client.scan_iter(match="task:*", count=100):
                task_id = key.decode("utf-8").split(":", 1)[1]
                if task_id in self.tasks:
                    continue  # 已在内存
                data = self.redis_client.get(key)
                if not data:
                    continue
                task_dict = json.loads(data)
                task = self._dict_to_task_info(task_dict)
                self.tasks[task_id] = task
        except Exception as e:
            logger.error(f"批量加载Redis任务失败: {e}")
    
    def get_user_tasks(self, user_id: int, status_filter: List[TaskStatus] = None) -> List[TaskInfo]:
        """获取用户的任务列表"""
        # 确保最新数据已加载
        self._load_tasks_from_redis()

        user_tasks = []
        
        for task in self.tasks.values():
            if task.user_id == user_id:
                if not status_filter or task.status in status_filter:
                    user_tasks.append(task)
        
        return sorted(user_tasks, key=lambda t: t.updated_at, reverse=True)
    
    def get_active_tasks(self) -> List[TaskInfo]:
        """获取所有活跃任务"""
        # 确保最新数据已加载
        self._load_tasks_from_redis()

        active_statuses = [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROCESSING, TaskStatus.RETRY]
        return [task for task in self.tasks.values() if task.status in active_statuses]
    
    def get_task_statistics(self) -> Dict[str, int]:
        """获取任务统计信息"""
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0
        }
        
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                stats["pending"] += 1
            elif task.status == TaskStatus.STARTED:
                stats["running"] += 1
            elif task.status == TaskStatus.SUCCESS:
                stats["completed"] += 1
            elif task.status == TaskStatus.FAILURE:
                stats["failed"] += 1
        
        return stats
    
    def cleanup_invalid_tasks(self) -> int:
        """清理无效的任务（如旧的drawing_analysis任务）"""
        cleaned_count = 0
        
        # 获取所有任务
        task_ids_to_remove = []
        
        for task_id, task in self.tasks.items():
            # 清理名称包含drawing_analysis的任务（不管时间，全部清理）
            if task.name.startswith("drawing_analysis:"):
                task_ids_to_remove.append(task_id)
        
        # 移除无效任务
        for task_id in task_ids_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
                # 也从Redis中清理
                try:
                    self.redis_client.delete(f"task:{task_id}")
                except Exception as e:
                    logger.error(f"从Redis清理任务失败: {e}")
                cleaned_count += 1
        
        logger.info(f"清理了 {cleaned_count} 个无效任务")
        return cleaned_count
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务 - 添加状态验证"""
        if task_id not in self.tasks:
            return False
        
        # 检查任务是否已经完成 - 防止错误取消
        task = self.tasks[task_id]
        if task.progress == 100 and task.status == TaskStatus.SUCCESS:
            logger.warning(f"尝试取消已完成的任务: {task_id}")
            return False
        
        await self.update_task_status(
            task_id=task_id,
            status=TaskStatus.REVOKED,
            stage=TaskStage.FAILED,
            message="任务已被取消",
            error_message="用户取消了任务"
        )
        
        # 这里可以添加实际的任务取消逻辑（如Celery revoke）
        logger.info(f"任务已取消: {task_id}")
        return True
    
    async def handle_websocket_error(self, task_id: str, error: Exception):
        """处理WebSocket错误 - 不应标记为用户取消"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            # 如果任务已完成，不要因为WebSocket错误而改变状态
            if task.progress == 100 and task.status == TaskStatus.SUCCESS:
                logger.warning(f"WebSocket错误但任务已完成，保持成功状态: {task_id}")
                return
        
        await self.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,  # 而不是REVOKED
            stage=TaskStage.FAILED,
            message="WebSocket连接异常",
            error_message=f"系统错误: {str(error)}"
        )
        
        logger.error(f"WebSocket错误处理: {task_id} - {error}")
    
    async def recover_completed_tasks(self):
        """恢复已完成但状态错误的任务"""
        from ..database import get_db
        from ..models.drawing import Drawing
        
        db = next(get_db())
        try:
            # 查找数据库中已上传但任务管理器中状态错误的图纸
            drawings = db.query(Drawing).filter(
                Drawing.status == "uploaded",
                Drawing.task_id.isnot(None)
            ).all()
            
            for drawing in drawings:
                task = self.get_task(drawing.task_id)
                if task and task.status == TaskStatus.REVOKED:
                    logger.info(f"恢复错误标记的任务: {drawing.task_id}")
                    
                    await self.update_task_status(
                        task_id=drawing.task_id,
                        status=TaskStatus.SUCCESS,
                        stage=TaskStage.COMPLETED,
                        progress=100,
                        message="图纸处理完成 - 状态已恢复",
                        error_message=None
                    )
                    
        except Exception as e:
            logger.error(f"恢复任务状态失败: {e}")
        finally:
            db.close()
    
    async def cleanup_expired_tasks(self):
        """清理过期任务"""
        cutoff_time = datetime.now() - timedelta(days=1)
        expired_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.updated_at < cutoff_time and task.status in [
                TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED
            ]:
                expired_tasks.append(task_id)
        
        for task_id in expired_tasks:
            del self.tasks[task_id]
            try:
                self.redis_client.delete(f"task:{task_id}")
            except Exception as e:
                logger.error(f"删除Redis任务失败: {e}")
        
        if expired_tasks:
            logger.info(f"清理了 {len(expired_tasks)} 个过期任务")

    def _safe_async_run(self, coro):
        """在当前循环或新事件循环中安全运行协程"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            asyncio.run(coro)

    # ------------------------------------------------------------------
    # Redis PubSub 监听 - 仅在有WebSocket能力的进程中需要
    # ------------------------------------------------------------------
    def _pubsub_listener(self):
        try:
            pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe("task_updates")
            logger.info("任务状态订阅线程已启动，监听 task_updates 频道")

            for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    raw = message["data"]
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    data = json.loads(raw)
                    task_id = data.get("task_id")
                    if not task_id:
                        continue
                    # 更新本地缓存
                    self.tasks[task_id] = self._dict_to_task_info(data)
                    # 推送到内部WebSocket集合
                    asyncio.run(self._broadcast_task_update(self.tasks[task_id]))

                    # 触发外部WebSocket回调（RealTimeConnectionManager）
                    websocket_callback = getattr(self, "_websocket_push_callback", None)
                    if websocket_callback:
                        try:
                            asyncio.run(websocket_callback(task_id, data))
                        except Exception as e:
                            logger.debug(f"回调推送失败: {e}")
                except Exception as e:
                    logger.debug(f"处理任务更新消息失败: {e}")
        except Exception as e:
            logger.error(f"PubSub监听线程异常: {e}")

    def cleanup_user_old_tasks(self, user_id: int, keep_hours: int = 24) -> int:
        """清理用户的旧任务"""
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=keep_hours)
        
        # 获取用户的任务
        user_tasks = self.get_user_tasks(user_id)
        
        # 找出需要清理的任务
        tasks_to_remove = []
        for task in user_tasks:
            # 清理超过指定时间的已完成/失败任务
            if (task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED] and 
                task.updated_at < cutoff_time):
                tasks_to_remove.append(task.task_id)
            # 或者清理旧的drawing_analysis任务（不管时间）
            elif task.name.startswith("drawing_analysis:"):
                tasks_to_remove.append(task.task_id)
        
        # 移除任务
        for task_id in tasks_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
                # 也从Redis中清理
                try:
                    self.redis_client.delete(f"task:{task_id}")
                except Exception as e:
                    logger.error(f"从Redis清理任务失败: {e}")
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"为用户 {user_id} 清理了 {cleaned_count} 个旧任务")
        
        return cleaned_count
    
    def cleanup_user_all_non_active_tasks(self, user_id: int) -> int:
        """清理用户的所有非活跃任务（强力清理模式）"""
        cleaned_count = 0
        
        # 获取用户的任务
        user_tasks = self.get_user_tasks(user_id)
        logger.info(f"准备清理用户 {user_id} 的非活跃任务，当前任务总数: {len(user_tasks)}")
        
        # 活跃状态的任务不清理
        active_statuses = [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROCESSING, TaskStatus.RETRY]
        
        # 找出需要清理的任务（所有非活跃任务）
        tasks_to_remove = []
        active_tasks = []
        
        for task in user_tasks:
            if task.status in active_statuses:
                active_tasks.append(task)
                logger.info(f"保留活跃任务: {task.task_id} - {task.name} ({task.status.value})")
            else:
                tasks_to_remove.append(task.task_id)
                logger.info(f"将清理任务: {task.task_id} - {task.name} ({task.status.value})")
        
        # 移除所有非活跃任务
        for task_id in tasks_to_remove:
            if task_id in self.tasks:
                del self.tasks[task_id]
                # 也从Redis中清理
                try:
                    self.redis_client.delete(f"task:{task_id}")
                except Exception as e:
                    logger.error(f"从Redis清理任务失败: {e}")
                cleaned_count += 1
        
        logger.info(f"为用户 {user_id} 清理了 {cleaned_count} 个非活跃任务，剩余 {len(active_tasks)} 个活跃任务")
        
        return cleaned_count

    def get_user_active_tasks(self, user_id: int) -> List[TaskInfo]:
        """获取用户的活跃任务（只返回运行中的任务）"""
        # 确保最新数据已加载
        self._load_tasks_from_redis()
        
        # 清理用户的旧任务
        self.cleanup_user_old_tasks(user_id)
        
        active_statuses = [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROCESSING, TaskStatus.RETRY]
        user_tasks = []
        
        for task in self.tasks.values():
            if task.user_id == user_id and task.status in active_statuses:
                user_tasks.append(task)
        
        return sorted(user_tasks, key=lambda t: t.updated_at, reverse=True)
    
    def get_user_recent_tasks(self, user_id: int, max_tasks: int = 10) -> List[TaskInfo]:
        """获取用户最近的任务（包括活跃任务和最近完成的任务）"""
        # 确保最新数据已加载
        self._load_tasks_from_redis()
        
        # 清理用户的旧任务
        self.cleanup_user_old_tasks(user_id, keep_hours=2)  # 只保留2小时内的任务
        
        user_tasks = []
        cutoff_time = datetime.now() - timedelta(hours=2)  # 只显示2小时内的任务
        
        for task in self.tasks.values():
            if task.user_id == user_id:
                # 活跃任务总是显示
                if task.status in [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.PROCESSING, TaskStatus.RETRY]:
                    user_tasks.append(task)
                # 最近2小时内完成的任务也显示
                elif task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE] and task.updated_at >= cutoff_time:
                    user_tasks.append(task)
        
        # 按更新时间排序，限制数量
        user_tasks = sorted(user_tasks, key=lambda t: t.updated_at, reverse=True)
        return user_tasks[:max_tasks]

# 创建全局任务管理器实例
task_manager = RealTimeTaskManager()

# 导出所有需要的类和枚举
__all__ = [
    'TaskStatus',
    'TaskStage', 
    'TaskInfo',
    'RealTimeTaskManager'
] 