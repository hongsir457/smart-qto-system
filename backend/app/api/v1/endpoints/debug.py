from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.debug_tools import CalculationDebugger
from app.models.user import User
from app.api.deps import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/calculation/{drawing_id}")
async def debug_calculation(
    drawing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """调试图纸计算流水线"""
    try:
        debugger = CalculationDebugger()
        results = debugger.check_calculation_pipeline(drawing_id)
        
        # 添加调试时间戳
        import datetime
        results['debug_timestamp'] = datetime.datetime.now().isoformat()
        results['debug_user'] = current_user.username
        
        return {
            "success": True,
            "data": results
        }
        
    except Exception as e:
        logger.error(f"调试失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"调试失败: {str(e)}")

@router.get("/logs/{drawing_id}")
async def get_task_logs(
    drawing_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务日志"""
    try:
        debugger = CalculationDebugger()
        logs = debugger.get_latest_task_logs(drawing_id, limit)
        
        return {
            "success": True,
            "data": logs
        }
        
    except Exception as e:
        logger.error(f"获取日志失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@router.post("/recalculate/{drawing_id}")
async def force_recalculate(
    drawing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """强制重新计算工程量"""
    try:
        from app.tasks.drawing_tasks import process_drawing_celery_task
        from app.models.drawing import Drawing
        from app.tasks.real_time_task_manager import RealTimeTaskManager
        import uuid
        
        # 检查图纸是否存在
        drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        # 重置状态
        drawing.status = "pending"
        drawing.error_message = None
        db.commit()
        
        # 生成新的实时任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化实时任务管理器
        task_manager = RealTimeTaskManager()
        
        # 启动处理任务
        celery_task = process_drawing_celery_task.delay(drawing_id, task_id)
        
        # 更新任务ID
        drawing.task_id = celery_task.id
        db.commit()
        
        return {
            "success": True,
            "message": "已启动重新计算",
            "task_id": celery_task.id,
            "real_time_task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"重新计算失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重新计算失败: {str(e)}") 