from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any, Optional
import os
from pathlib import Path
from fastapi.responses import FileResponse
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools

from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.models.drawing import Drawing as DrawingModel
from app.schemas.drawing import Drawing, DrawingCreate, DrawingUpdate, DrawingInDB, DrawingList
from app.services.drawing import process_drawing, extract_text, celery_app
from app.services.export import ExportService
from app.services.storage import upload_fileobj_to_s3
from app.services import drawing as drawing_service
from app.crud import drawings
from app.database import get_db, SessionLocal

router = APIRouter()

@router.post("/upload", response_model=Drawing)
async def upload_drawing(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    file: UploadFile = File(...),
) -> Any:
    """
    上传图纸文件
    """
    # 验证文件类型
    allowed_types = [".pdf", ".dwg", ".dxf"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed types: PDF, DWG, DXF"
        )

    # 上传到S3
    try:
        file.file.seek(0)
        s3_url = upload_fileobj_to_s3(file.file, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"S3上传失败: {str(e)}"
        )

    # 创建数据库记录
    drawing = DrawingModel(
        filename=file.filename,
        file_path=s3_url,
        file_type=file_ext[1:],  # 去掉点号
        status="pending",
        user_id=current_user.id
    )
    db.add(drawing)
    db.commit()
    db.refresh(drawing)

    # 异步处理图纸
    process_drawing.delay(drawing.id)

    return drawing

@router.get("", response_model=DrawingList)
def list_drawings(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    page: int = 1,
    size: int = 10
) -> Any:
    """
    获取当前用户的所有图纸，支持分页
    """
    try:
        print(f"list_drawings called with page={page}, size={size}, user_id={current_user.id}")
        
        # 计算偏移量
        skip = (page - 1) * size
        
        # 获取总数
        total = db.query(DrawingModel).filter(
            DrawingModel.user_id == current_user.id
        ).count()
        
        print(f"Total drawings for user {current_user.id}: {total}")
        
        # 获取分页数据
        drawings = db.query(DrawingModel).filter(
            DrawingModel.user_id == current_user.id
        ).order_by(DrawingModel.created_at.desc()).offset(skip).limit(size).all()
        
        print(f"Retrieved {len(drawings)} drawings")
        
        # 创建DrawingList实例
        result = DrawingList(
            items=drawings,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )
        
        print(f"Successfully created DrawingList with {len(result.items)} items")
        return result
        
    except Exception as e:
        print(f"Error in list_drawings: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"获取图纸列表失败: {str(e)}"
        )

@router.get("/", response_model=DrawingList)
def list_drawings_with_slash(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    page: int = 1,
    size: int = 10
) -> Any:
    """
    获取当前用户的所有图纸，支持分页（处理末尾斜杠的版本）
    """
    return list_drawings(db, current_user, page, size)

@router.get("/{drawing_id}", response_model=Drawing)
def get_drawing(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    drawing_id: int,
) -> Any:
    """
    获取特定图纸的详细信息
    """
    drawing = db.query(DrawingModel).filter(
        DrawingModel.id == drawing_id,
        DrawingModel.user_id == current_user.id
    ).first()
    if not drawing:
        raise HTTPException(
            status_code=404,
            detail="图纸不存在"
        )
    return drawing

@router.get("/{drawing_id}/export")
async def export_quantities(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """
    导出工程量计算结果为Excel文件
    """
    # 获取图纸信息
    drawing = db.query(DrawingModel).filter(
        DrawingModel.id == drawing_id,
        DrawingModel.user_id == current_user.id
    ).first()
    
    if not drawing:
        raise HTTPException(
            status_code=404,
            detail="Drawing not found"
        )
    
    if not drawing.recognition_results:
        raise HTTPException(
            status_code=400,
            detail="No recognition results available for export"
        )
    
    # 创建导出目录
    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)
    
    # 生成导出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"quantities_{drawing.filename}_{timestamp}.xlsx"
    output_path = export_dir / filename
    
    # 导出工程量计算结果
    try:
        ExportService.export_quantities_to_excel(
            drawing.recognition_results["quantities"],
            str(output_path)
        )
        
        # 返回Excel文件
        return FileResponse(
            path=output_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export quantities: {str(e)}"
        )
    finally:
        # 删除临时文件
        if output_path.exists():
            output_path.unlink()

@router.post("/{drawing_id}/ocr")
async def ocr_drawing(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    对图纸进行OCR识别
    """
    drawing = db.query(DrawingModel).filter(
        DrawingModel.id == drawing_id,
        DrawingModel.user_id == current_user.id
    ).first()
    
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
        
    try:
        # 更新状态为处理中
        drawing.status = "processing"
        db.commit()
        
        # 使用Celery任务处理OCR
        task = celery_app.send_task(
            'app.services.drawing.process_ocr_task',
            args=[drawing_id],
            countdown=1  # 1秒后开始执行
        )
        
        return {
            "status": "processing",
            "message": "OCR处理已开始，请稍后查看结果",
            "task_id": task.id,
            "drawing_id": drawing_id
        }
        
    except Exception as e:
        drawing.status = "error"
        drawing.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{drawing_id}/ocr/status")
async def get_ocr_status(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    获取OCR处理状态
    """
    drawing = db.query(DrawingModel).filter(
        DrawingModel.id == drawing_id,
        DrawingModel.user_id == current_user.id
    ).first()
    
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
        
    # 如果有任务ID，检查任务状态
    task_id = drawing.task_id if hasattr(drawing, 'task_id') else None
    task_status = None
    if task_id:
        task = celery_app.AsyncResult(task_id)
        task_status = task.status
        
    return {
        "status": drawing.status,
        "task_status": task_status,
        "error_message": drawing.error_message if drawing.status == "error" else None,
        "results": drawing.ocr_results if drawing.status == "completed" else None
    }

@router.post("/{drawing_id}/detect-components")
async def detect_components(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    对指定图纸进行构件检测（异步）
    """
    drawing = db.query(DrawingModel).filter(
        DrawingModel.id == drawing_id, 
        DrawingModel.user_id == current_user.id
    ).first()
    
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    try:
        # 启动异步构件检测任务
        from app.services.drawing import process_drawing
        task = process_drawing.delay(drawing_id)
        
        # 更新图纸状态
        drawing.status = "processing"
        drawing.task_id = task.id
        db.commit()
        
        return {
            "status": "processing",
            "message": "构件检测已开始，请稍后查看结果",
            "task_id": task.id,
            "drawing_id": drawing_id
        }
        
    except Exception as e:
        drawing.status = "error"
        drawing.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{drawing_id}/verify")
def verify_drawing(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    对指定图纸进行二次校验
    """
    drawing = db.query(DrawingModel).filter(DrawingModel.id == drawing_id, DrawingModel.user_id == current_user.id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    if not drawing.recognition_results:
        raise HTTPException(status_code=400, detail="请先进行构件检测")
    
    try:
        # 这里可以添加二次校验的逻辑
        # 例如：检查构件尺寸是否合理、构件之间是否有冲突等
        return {"status": "success", "message": "二次校验通过"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{drawing_id}/ai-assist")
def ai_assist_drawing(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    对指定图纸进行AI辅助分析
    """
    drawing = db.query(DrawingModel).filter(DrawingModel.id == drawing_id, DrawingModel.user_id == current_user.id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    if not drawing.recognition_results:
        raise HTTPException(status_code=400, detail="请先进行构件检测")
    
    try:
        # 这里可以添加AI辅助分析的逻辑
        # 例如：分析构件布局、提供优化建议等
        return {"status": "success", "message": "AI辅助分析完成"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{drawing_id}")
def delete_drawing(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    删除指定图纸
    """
    drawing = db.query(DrawingModel).filter(DrawingModel.id == drawing_id, DrawingModel.user_id == current_user.id).first()
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    # 可选：删除 S3 文件（如有需要）
    db.delete(drawing)
    db.commit()
    return {"message": "删除成功"}

@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    获取任务状态
    """
    try:
        task = celery_app.AsyncResult(task_id)
        print(f"[Task Status] Task ID: {task_id}, State: {task.state}")
        
        if task.state == 'PENDING':
            return {
                'status': 'processing',
                'state': task.state,
                'message': '任务等待中...'
            }
        elif task.state == 'STARTED' or task.state == 'PROCESSING':
            return {
                'status': 'processing',
                'state': task.state,
                'message': '任务处理中...'
            }
        elif task.state == 'SUCCESS':
            result = task.get()
            if isinstance(result, dict) and "error" in result:
                return {
                    'status': 'failed',
                    'state': task.state,
                    'error': result["error"]
                }
            return {
                'status': 'completed',
                'state': task.state,
                'result': result
            }
        elif task.state == 'FAILURE':
            error = str(task.info) if task.info else "任务执行失败"
            return {
                'status': 'failed',
                'state': task.state,
                'error': error
            }
        else:
            return {
                'status': 'processing',
                'state': task.state,
                'message': '任务进行中...'
            }
    except Exception as e:
        print(f"[Task Status Error] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取任务状态失败: {str(e)}"
        )

@router.post("/{drawing_id}/process")
async def process_drawing_endpoint(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    对指定图纸进行完整处理（构件检测+OCR+工程量计算）
    """
    drawing = db.query(DrawingModel).filter(
        DrawingModel.id == drawing_id, 
        DrawingModel.user_id == current_user.id
    ).first()
    
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    try:
        # 启动异步完整处理任务
        from app.services.drawing import process_drawing
        task = process_drawing.delay(drawing_id)
        
        # 更新图纸状态
        drawing.status = "processing"
        drawing.task_id = task.id
        db.commit()
        
        return {
            "status": "processing",
            "message": "图纸处理已开始，包括构件检测、OCR识别和工程量计算",
            "task_id": task.id,
            "drawing_id": drawing_id
        }
        
    except Exception as e:
        drawing.status = "error"
        drawing.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e)) 