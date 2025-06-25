"""
图纸删除相关API
从原drawings.py中提取的删除功能
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import os
from datetime import datetime

from ....database import get_db
from ....models.drawing import Drawing
from ...deps import get_current_user
from ....models.user import User
from ....tasks import task_manager, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()

@router.delete("/{drawing_id}")
async def delete_drawing(
    drawing_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除指定图纸
    """
    logger.info(f"🗑️  删除图纸请求: drawing_id={drawing_id}, user_id={current_user.id}, username={current_user.username}")
    
    try:
        # 查找图纸
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            # 检查图纸是否存在（不考虑用户ID）
            drawing_any_user = db.query(Drawing).filter(Drawing.id == drawing_id).first()
            if drawing_any_user:
                logger.warning(f"❌ 用户权限不足: user_id={current_user.id} 试图删除图纸 {drawing_id}，但图纸属于用户 {drawing_any_user.user_id}")
                raise HTTPException(status_code=403, detail="无权删除此图纸")
            else:
                logger.warning(f"❌ 图纸不存在: drawing_id={drawing_id}")
                raise HTTPException(status_code=404, detail="图纸不存在")
        
        logger.info(f"📋 图纸信息: filename={drawing.filename}, status={drawing.status}")
        
        # 检查是否正在处理中
        if drawing.status == "processing" and not force:
            logger.warning(f"⚠️  图纸正在处理中，无法删除: drawing_id={drawing_id}, status={drawing.status}")
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "图纸正在处理中，无法删除",
                    "status": "processing",
                    "suggestion": "请等待处理完成或使用强制删除",
                    "can_force_delete": True,
                    "drawing_id": drawing_id,
                    "filename": drawing.filename
                }
            )
        
        # 查找并清理相关任务
        related_tasks = []
        for task_id, task in task_manager.tasks.items():
            if (task.metadata and 
                task.metadata.get("drawing_id") == drawing_id and 
                task.user_id == current_user.id):
                related_tasks.append(task_id)
        
        logger.info(f"🔄 找到 {len(related_tasks)} 个相关任务: {related_tasks}")
        
        # 如果是强制删除，先尝试取消任务
        if drawing.status == "processing" and force:
            logger.info(f"🔥 强制删除处理中的图纸: drawing_id={drawing_id}")
            # 尝试取消Celery任务
            if drawing.task_id:
                try:
                    from celery import Celery
                    from ....core.config import settings
                    celery_app = Celery('smart_qto_system')
                    celery_app.conf.update(
                        broker_url=settings.CELERY_BROKER_URL,
                        result_backend=settings.CELERY_RESULT_BACKEND
                    )
                    celery_app.control.revoke(drawing.task_id, terminate=True)
                    logger.info(f"✅ 已尝试取消任务: task_id={drawing.task_id}")
                except Exception as e:
                    logger.warning(f"⚠️  取消任务失败: {str(e)}")
            
            # 强制更新状态为cancelled
            drawing.status = "cancelled"
            drawing.error_message = f"任务被用户强制取消 (删除时间: {datetime.now()})"
            db.commit()
        
        # 清理任务管理器中的相关任务
        for task_id in related_tasks:
            try:
                await task_manager.cancel_task(task_id)
                logger.info(f"✅ 已取消任务: {task_id}")
            except Exception as e:
                logger.warning(f"⚠️  取消任务失败 {task_id}: {str(e)}")
        
        # 使用文件生命周期管理器进行完整删除
        from ....core.file_strategy import FileLifecycleManager
        from ....services.s3_service import s3_service
        
        file_manager = FileLifecycleManager(s3_service=s3_service, db_session=db)
        delete_result = await file_manager.delete_file_completely(drawing_id, current_user.id)
        
        if not delete_result["success"]:
            logger.error(f"❌ 文件删除失败: {delete_result}")
            raise HTTPException(status_code=500, detail=f"删除失败: {delete_result.get('message', '未知错误')}")
        
        # 记录删除详情
        filename = delete_result["filename"]
        logger.info(f"✅ 文件完整删除成功:")
        logger.info(f"  - S3删除: {delete_result['s3_deleted']}")
        logger.info(f"  - 本地删除: {delete_result['local_deleted']}")
        logger.info(f"  - 数据库删除: {delete_result['db_deleted']}")
        if delete_result["errors"]:
            logger.warning(f"  - 警告: {delete_result['errors']}")
        
        logger.info(f"✅ 已删除图纸: {filename} (ID: {drawing_id})")
        
        # 推送图纸删除事件到WebSocket
        try:
            websocket_callback = getattr(task_manager, "_websocket_push_callback", None)
            if websocket_callback:
                await websocket_callback("drawing_deleted", {
                    "type": "drawing_deleted",
                    "drawing_id": drawing_id,
                    "filename": filename,
                    "user_id": current_user.id,
                    "deleted_tasks": related_tasks,
                    "message": f"图纸 '{filename}' 已删除"
                })
        except Exception as e:
            logger.warning(f"推送删除事件失败: {str(e)}")
        
        return {
            "message": f"图纸 '{filename}' 删除成功",
            "drawing_id": drawing_id,
            "deleted_tasks": len(related_tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除图纸失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.delete("/batch")
async def batch_delete_drawings(
    drawing_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量删除图纸
    """
    try:
        if len(drawing_ids) > 20:  # 限制批量删除数量
            raise HTTPException(status_code=400, detail="单次最多删除20个图纸")
        
        results = []
        
        for drawing_id in drawing_ids:
            try:
                # 查找图纸
                drawing = db.query(Drawing).filter(
                    Drawing.id == drawing_id,
                    Drawing.user_id == current_user.id
                ).first()
                
                if not drawing:
                    results.append({
                        "drawing_id": drawing_id,
                        "status": "error",
                        "message": "图纸不存在"
                    })
                    continue
                
                # 检查是否正在处理中
                if drawing.status == "processing":
                    results.append({
                        "drawing_id": drawing_id,
                        "status": "error",
                        "message": "图纸正在处理中，无法删除"
                    })
                    continue
                
                # 使用文件生命周期管理器进行完整删除
                from ....core.file_strategy import FileLifecycleManager
                from ....services.s3_service import s3_service
                
                file_manager = FileLifecycleManager(s3_service=s3_service, db_session=db)
                delete_result = await file_manager.delete_file_completely(drawing_id, current_user.id)
                
                if delete_result["success"]:
                    results.append({
                        "drawing_id": drawing_id,
                        "status": "success",
                        "message": f"图纸 '{delete_result['filename']}' 删除成功",
                        "details": {
                            "s3_deleted": delete_result['s3_deleted'],
                            "local_deleted": delete_result['local_deleted'],
                            "db_deleted": delete_result['db_deleted']
                        }
                    })
                else:
                    results.append({
                        "drawing_id": drawing_id,
                        "status": "error",
                        "message": delete_result.get('message', '删除失败'),
                        "errors": delete_result.get('errors', [])
                    })
                
            except Exception as e:
                logger.error(f"删除图纸 {drawing_id} 失败: {str(e)}")
                results.append({
                    "drawing_id": drawing_id,
                    "status": "error",
                    "message": str(e)
                })
        
        successful_deletions = len([r for r in results if r["status"] == "success"])
        
        return {
            "total_requested": len(drawing_ids),
            "successful_deletions": successful_deletions,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}") 