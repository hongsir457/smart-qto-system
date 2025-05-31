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

@router.get("/", response_model=DrawingList)
def get_drawings(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    获取图纸列表
    """
    drawings_data = drawings.get_multi_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    total = drawings.count_by_user(db, user_id=current_user.id)
    
    return DrawingList(
        items=drawings_data,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/{drawing_id}", response_model=Drawing)
def get_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取单个图纸详情
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    return drawing

@router.put("/{drawing_id}", response_model=Drawing)
def update_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    drawing_in: DrawingUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新图纸信息
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    drawing = drawings.update(db, db_obj=drawing, obj_in=drawing_in)
    return drawing

@router.delete("/{drawing_id}")
def delete_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除图纸
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    drawings.remove(db, id=drawing_id)
    return {"message": "图纸删除成功"}

@router.get("/{drawing_id}/download")
def download_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    下载图纸文件
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    # 如果是S3 URL，重定向到S3
    if drawing.file_path.startswith('http'):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=drawing.file_path)
    
    # 本地文件
    file_path = Path(drawing.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=drawing.filename,
        media_type='application/octet-stream'
    )

@router.get("/{drawing_id}/preview")
def preview_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    预览图纸
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    # 返回预览信息
    return {
        "id": drawing.id,
        "filename": drawing.filename,
        "file_type": drawing.file_type,
        "status": drawing.status,
        "preview_url": drawing.file_path if drawing.file_path.startswith('http') else None,
        "text_content": drawing.text_content,
        "recognition_results": drawing.recognition_results
    }

@router.post("/{drawing_id}/reprocess")
def reprocess_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    重新处理图纸
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    # 重置状态并重新处理
    drawing.status = "pending"
    drawing.error_message = None
    drawing.recognition_results = None
    db.commit()
    
    # 启动异步处理
    process_drawing.delay(drawing.id)
    
    return {"message": "重新处理已启动"}

@router.get("/tasks/{task_id}")
def get_task_status(task_id: str) -> Any:
    """
    获取任务状态
    """
    task = celery_app.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'pending',
            'message': '任务等待中'
        }
    elif task.state == 'PROCESSING':
        response = {
            'status': 'processing',
            'message': '正在处理',
            'progress': task.info.get('progress', 0) if task.info else 0
        }
    elif task.state == 'SUCCESS':
        response = {
            'status': 'completed',
            'result': task.result
        }
    else:  # FAILURE
        response = {
            'status': 'failed',
            'error': str(task.info)
        }
    
    return response

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

@router.get("/{drawing_id}/export")
def export_drawing(
    *,
    db: Session = Depends(deps.get_db),
    drawing_id: int,
    format: str = "excel",
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    导出图纸分析结果
    """
    drawing = drawings.get_by_id_and_user(db, id=drawing_id, user_id=current_user.id)
    if not drawing:
        raise HTTPException(status_code=404, detail="图纸不存在")
    
    if not drawing.recognition_results:
        raise HTTPException(status_code=400, detail="暂无识别结果可导出")
    
    export_service = ExportService()
    
    if format.lower() == "excel":
        file_path = export_service.export_to_excel(drawing)
        return FileResponse(
            path=file_path,
            filename=f"{drawing.filename}_analysis.xlsx",
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    elif format.lower() == "pdf":
        file_path = export_service.export_to_pdf(drawing)
        return FileResponse(
            path=file_path,
            filename=f"{drawing.filename}_analysis.pdf",
            media_type='application/pdf'
        )
    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式")

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

# DWG多图框处理相关端点
@router.post("/{drawing_id}/process-dwg-multi-sheets")
async def process_dwg_multi_sheets(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    处理DWG文件的多图框识别
    """
    try:
        # 检查图纸是否存在
        drawing = db.query(DrawingModel).filter(
            DrawingModel.id == drawing_id, 
            DrawingModel.user_id == current_user.id
        ).first()
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        # 检查文件类型
        if not drawing.file_path.lower().endswith(('.dwg', '.dxf')):
            raise HTTPException(status_code=400, detail="只支持DWG/DXF文件的多图框处理")
        
        # 检查是否已有任务在运行
        if drawing.status == "processing":
            return {
                "message": "任务已在处理中",
                "status": "processing",
                "task_id": drawing.task_id
            }
        
        # 启动Celery任务
        from app.services.drawing import process_dwg_multi_sheets
        task = process_dwg_multi_sheets.delay(drawing_id)
        
        # 更新图纸状态
        drawing.status = "processing"
        drawing.task_id = task.id
        drawing.error_message = None
        db.commit()
        
        return {
            "message": "DWG多图框处理任务已启动",
            "task_id": task.id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"启动DWG多图框处理任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")

@router.get("/{drawing_id}/dwg-multi-sheets-status")
async def get_dwg_multi_sheets_status(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    获取DWG多图框处理状态
    """
    try:
        drawing = db.query(DrawingModel).filter(
            DrawingModel.id == drawing_id, 
            DrawingModel.user_id == current_user.id
        ).first()
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.task_id:
            return {
                "status": "not_started",
                "message": "任务尚未启动"
            }
        
        # 获取Celery任务状态
        from app.core.celery_app import celery_app
        task = celery_app.AsyncResult(drawing.task_id)
        
        if task.state == 'PENDING':
            return {
                "status": "pending",
                "message": "任务等待中"
            }
        elif task.state == 'STARTED':
            return {
                "status": "started",
                "message": "任务已开始",
                "meta": task.info
            }
        elif task.state == 'PROCESSING':
            return {
                "status": "processing",
                "message": "正在处理",
                "meta": task.info
            }
        elif task.state == 'SUCCESS':
            result = task.result
            return {
                "status": "completed",
                "message": "处理完成",
                "result": result,
                "recognition_results": drawing.recognition_results
            }
        elif task.state == 'FAILURE':
            return {
                "status": "failed",
                "message": "处理失败",
                "error": str(task.info)
            }
        else:
            return {
                "status": task.state.lower(),
                "message": f"任务状态: {task.state}",
                "meta": task.info if hasattr(task, 'info') else None
            }
            
    except Exception as e:
        print(f"获取DWG多图框处理状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@router.get("/{drawing_id}/dwg-drawings-list")
async def get_dwg_drawings_list(
    drawing_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    获取DWG文件中的图纸列表
    """
    try:
        drawing = db.query(DrawingModel).filter(
            DrawingModel.id == drawing_id, 
            DrawingModel.user_id == current_user.id
        ).first()
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.recognition_results:
            return {
                "message": "尚未进行多图框处理",
                "drawings": []
            }
        
        recognition_results = drawing.recognition_results
        
        if recognition_results.get("type") != "multiple_drawings":
            return {
                "message": "该文件不是多图框DWG文件",
                "drawings": []
            }
        
        # 提取图纸列表信息
        drawings_list = []
        for idx, drawing_data in enumerate(recognition_results.get("drawings", [])):
            drawings_list.append({
                "index": idx + 1,
                "number": drawing_data.get("number", f"图纸{idx + 1}"),
                "title": drawing_data.get("title", ""),
                "scale": drawing_data.get("scale", ""),
                "components": drawing_data.get("components", {}),
                "quantities": drawing_data.get("quantities", {}),
                "summary": drawing_data.get("summary", {}),
                "component_count": sum(drawing_data.get("components", {}).values())
            })
        
        return {
            "total_drawings": recognition_results.get("statistics", {}).get("total_drawings", 0),
            "processed_drawings": recognition_results.get("statistics", {}).get("processed_drawings", 0),
            "drawings": drawings_list,
            "overall_summary": recognition_results.get("recognition", {}).get("summary", {})
        }
        
    except Exception as e:
        print(f"获取DWG图纸列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图纸列表失败: {str(e)}") 