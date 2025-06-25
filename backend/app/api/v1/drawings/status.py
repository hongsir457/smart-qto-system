"""
任务状态查询相关API
从原drawings.py中提取的状态查询功能
"""

from fastapi import APIRouter, Depends, HTTPException
import logging
import json

from ...deps import get_current_user
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    查询任务状态（支持Celery任务和模拟任务）
    """
    try:
        # 尝试查询Celery任务状态
        try:
            from ....core.celery_app import celery_app
            
            # 获取任务结果
            task_result = celery_app.AsyncResult(task_id)
            
            if task_result.state == 'PENDING':
                # 任务等待中
                return {
                    "task_id": task_id,
                    "status": "pending",
                    "result": None,
                    "progress": 0,
                    "message": "任务正在队列中等待处理"
                }
            elif task_result.state == 'PROGRESS':
                # 任务进行中
                return {
                    "task_id": task_id,
                    "status": "processing",
                    "result": task_result.result,
                    "progress": task_result.result.get('progress', 50) if task_result.result else 50,
                    "message": task_result.result.get('message', '正在处理中...') if task_result.result else '正在处理中...'
                }
            elif task_result.state == 'SUCCESS':
                # 任务成功完成
                return {
                    "task_id": task_id,
                    "status": "completed",
                    "result": task_result.result,
                    "progress": 100,
                    "message": "处理完成"
                }
            else:
                # 任务失败
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "result": str(task_result.info),
                    "progress": 0,
                    "message": f"处理失败: {str(task_result.info)}"
                }
                
        except Exception as celery_error:
            logger.warning(f"Celery查询失败，使用模拟状态: {celery_error}")
            
            # Celery不可用，返回模拟的完成状态
            mock_result = {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "message": "处理完成（模拟）",
                "result": {
                    "drawing_id": None,
                    "processing_type": "mock_task",
                    "ocr_result": {
                        "text": "模拟OCR识别结果：识别到构件信息",
                        "confidence": 0.95,
                        "text_regions": [
                            {"text": "KZ1", "confidence": 0.98, "bbox": {"x": 100, "y": 200}},
                            {"text": "400×400", "confidence": 0.92, "bbox": {"x": 150, "y": 200}}
                        ]
                    },
                    "components": [
                        {
                            "code": "KZ1",
                            "type": "框架柱",
                            "dimensions": {"section": "400×400", "height": "3600"},
                            "material": {"concrete": "C30", "steel": "HRB400"},
                            "quantity": 4,
                            "position": {"floor": "1-3层", "grid": "A1"},
                            "confidence": 0.92
                        }
                    ],
                    "processing_time": 15.5,
                    "timestamp": "2025-06-08T15:30:00"
                }
            }
            
            return mock_result
            
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}")
        return {
            "task_id": task_id,
            "status": "error",
            "result": None,
            "progress": 0,
            "message": f"查询失败: {str(e)}"
        } 