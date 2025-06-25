"""
任务恢复管理器
处理Celery任务中断和恢复逻辑
"""

import logging
import redis
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.core.config import settings
from app.tasks.real_time_task_manager import RealTimeTaskManager, TaskStatus, TaskStage

logger = logging.getLogger(__name__)

class TaskRecoveryManager:
    """任务恢复管理器"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.task_manager = RealTimeTaskManager()
        
    def handle_unacknowledged_messages(self) -> Dict[str, Any]:
        """处理未确认的消息"""
        logger.info("🔍 检查未确认的任务消息...")
        
        try:
            # 获取所有活跃任务
            active_tasks = self._get_active_tasks()
            
            # 检查任务状态
            recovered_tasks = []
            failed_tasks = []
            
            for task_id, task_info in active_tasks.items():
                recovery_result = self._recover_task(task_id, task_info)
                
                if recovery_result['success']:
                    recovered_tasks.append(task_id)
                else:
                    failed_tasks.append({
                        'task_id': task_id,
                        'error': recovery_result['error']
                    })
            
            result = {
                'total_checked': len(active_tasks),
                'recovered': len(recovered_tasks),
                'failed': len(failed_tasks),
                'recovered_tasks': recovered_tasks,
                'failed_tasks': failed_tasks
            }
            
            logger.info(f"📊 任务恢复结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 任务恢复检查失败: {e}")
            return {'error': str(e)}
    
    def _get_active_tasks(self) -> Dict[str, Dict]:
        """获取所有活跃任务"""
        try:
            # 从Redis获取任务元数据
            task_keys = self.redis_client.keys('celery-task-meta-*')
            active_tasks = {}
            
            for key in task_keys:
                task_id = key.replace('celery-task-meta-', '')
                task_data = self.redis_client.get(key)
                
                if task_data:
                    try:
                        task_info = json.loads(task_data)
                        # 只处理未完成的任务
                        if task_info.get('status') in ['PENDING', 'STARTED', 'RETRY']:
                            active_tasks[task_id] = task_info
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ 无法解析任务数据: {key}")
            
            return active_tasks
            
        except Exception as e:
            logger.error(f"❌ 获取活跃任务失败: {e}")
            return {}
    
    def _recover_task(self, task_id: str, task_info: Dict) -> Dict[str, Any]:
        """恢复单个任务"""
        try:
            # 检查任务的最后更新时间
            date_done = task_info.get('date_done')
            if date_done:
                last_update = datetime.fromisoformat(date_done.replace('Z', '+00:00'))
                time_diff = datetime.now().timestamp() - last_update.timestamp()
                
                # 如果任务超过30分钟没有更新，标记为失败
                if time_diff > 1800:  # 30分钟
                    return self._mark_task_as_failed(
                        task_id, 
                        "任务超时，可能由于worker中断导致"
                    )
            
            # 检查任务是否真的在运行
            if self._is_task_really_running(task_id):
                logger.info(f"✅ 任务 {task_id} 正在正常运行")
                return {'success': True, 'action': 'no_action_needed'}
            else:
                # 任务不在运行，但状态显示为活跃，需要恢复
                return self._restart_task(task_id, task_info)
                
        except Exception as e:
            logger.error(f"❌ 恢复任务 {task_id} 失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _is_task_really_running(self, task_id: str) -> bool:
        """检查任务是否真的在运行"""
        try:
            # 检查实时任务管理器中的状态
            task = self.task_manager.get_task(task_id)
            if task:
                # 检查最后更新时间
                last_update = datetime.fromisoformat(task['updated_at'])
                time_diff = datetime.now() - last_update
                
                # 如果5分钟内有更新，认为任务在运行
                return time_diff < timedelta(minutes=5)
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ 检查任务运行状态失败: {e}")
            return False
    
    def _mark_task_as_failed(self, task_id: str, reason: str) -> Dict[str, Any]:
        """标记任务为失败"""
        try:
            # 更新Celery任务状态
            self.redis_client.set(
                f'celery-task-meta-{task_id}',
                json.dumps({
                    'status': 'FAILURE',
                    'result': {'error': reason},
                    'date_done': datetime.now().isoformat(),
                    'traceback': None
                }),
                ex=3600  # 1小时后过期
            )
            
            # 更新实时任务管理器
            import asyncio
            asyncio.run(self.task_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                stage=TaskStage.FAILED,
                message=reason,
                error_message=reason
            ))
            
            logger.info(f"✅ 任务 {task_id} 已标记为失败: {reason}")
            return {'success': True, 'action': 'marked_as_failed'}
            
        except Exception as e:
            logger.error(f"❌ 标记任务失败状态失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _restart_task(self, task_id: str, task_info: Dict) -> Dict[str, Any]:
        """重启任务"""
        try:
            # 这里可以实现任务重启逻辑
            # 目前先标记为失败，让用户手动重新提交
            return self._mark_task_as_failed(
                task_id,
                "任务因worker中断而失败，请重新提交"
            )
            
        except Exception as e:
            logger.error(f"❌ 重启任务失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_expired_tasks(self, max_age_hours: int = 24) -> int:
        """清理过期任务"""
        try:
            cleaned_count = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            task_keys = self.redis_client.keys('celery-task-meta-*')
            
            for key in task_keys:
                task_data = self.redis_client.get(key)
                if task_data:
                    try:
                        task_info = json.loads(task_data)
                        date_done = task_info.get('date_done')
                        
                        if date_done:
                            task_time = datetime.fromisoformat(date_done.replace('Z', '+00:00'))
                            if task_time < cutoff_time:
                                self.redis_client.delete(key)
                                cleaned_count += 1
                                
                    except (json.JSONDecodeError, ValueError):
                        # 删除损坏的任务数据
                        self.redis_client.delete(key)
                        cleaned_count += 1
            
            logger.info(f"🧹 清理了 {cleaned_count} 个过期任务")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ 清理过期任务失败: {e}")
            return 0

# 全局实例
task_recovery_manager = TaskRecoveryManager() 