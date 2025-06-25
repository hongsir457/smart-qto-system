#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务管理API路由
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from celery.result import AsyncResult

from app.core.celery_app import celery_app
from app.tasks.ocr_tasks import process_ocr_file_task, batch_process_ocr_files
from app.tasks import task_manager, TaskStatus, TaskStage
from app.core.config import settings

router = APIRouter()

# 请求模型
class TaskCreateRequest(BaseModel):
    file_path: str
    options: Optional[Dict[str, Any]] = {}

class BatchTaskCreateRequest(BaseModel):
    file_paths: List[str]
    options: Optional[Dict[str, Any]] = {}

# 响应模型
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    websocket_url: Optional[str] = None

class TaskProgressResponse(BaseModel):
    task_id: str
    status: str
    stage: str
    progress: int
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

@router.post("/tasks/ocr", response_model=TaskResponse)
async def create_ocr_task(
    file: UploadFile = File(...),
    options: str = Form("{}")
):
    """
    创建OCR处理任务
    
    上传文件并启动OCR处理任务，返回任务ID和WebSocket连接URL
    """
    try:
        # 解析选项
        import json
        task_options = json.loads(options) if options else {}
        
        # 验证文件类型
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.dwg', '.dxf'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}"
            )
        
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())
        
        # 保存上传的文件
        upload_dir = settings.UPLOAD_DIRECTORY
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{task_id}_{file.filename}")
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 启动Celery任务，使用自定义任务ID
        celery_task = process_ocr_file_task.apply_async(
            args=[file_path, task_options],
            task_id=task_id
        )
        
        # 初始化任务状态
        await task_manager.update_task_progress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            stage=TaskStage.UPLOAD,
            progress=0,
            message="任务已创建，等待处理...",
            details={
                "filename": file.filename,
                "file_size": len(content),
                "file_path": file_path,
                "options": task_options
            }
        )
        
        return TaskResponse(
            task_id=task_id,
            status="created",
            message="OCR任务已创建",
            websocket_url=f"ws://localhost:8000/api/v1/ws/task/{task_id}"
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的选项JSON格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.post("/tasks/batch-ocr", response_model=TaskResponse)
async def create_batch_ocr_task(request: BatchTaskCreateRequest):
    """
    创建批量OCR处理任务
    """
    try:
        # 验证文件路径
        for file_path in request.file_paths:
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=400,
                    detail=f"文件不存在: {file_path}"
                )
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 启动批量处理任务
        celery_task = batch_process_ocr_files.apply_async(
            args=[request.file_paths, request.options],
            task_id=task_id
        )
        
        # 初始化任务状态
        await task_manager.update_task_progress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            stage=TaskStage.UPLOAD,
            progress=0,
            message=f"批量任务已创建，准备处理 {len(request.file_paths)} 个文件...",
            details={
                "file_count": len(request.file_paths),
                "file_paths": request.file_paths,
                "options": request.options
            }
        )
        
        return TaskResponse(
            task_id=task_id,
            status="created", 
            message="批量OCR任务已创建",
            websocket_url=f"ws://localhost:8000/api/v1/ws/task/{task_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建批量任务失败: {str(e)}")

@router.get("/tasks/{task_id}/status", response_model=TaskProgressResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态
    """
    try:
        # 从任务管理器获取进度
        progress = await task_manager.get_task_progress(task_id)
        
        if not progress:
            # 尝试从Celery获取状态
            celery_result = AsyncResult(task_id, app=celery_app)
            celery_status = celery_result.status
            
            if celery_status == "PENDING":
                raise HTTPException(status_code=404, detail="任务不存在")
            
            # 返回基本的Celery状态
            return TaskProgressResponse(
                task_id=task_id,
                status=celery_status.lower(),
                stage="unknown",
                progress=0,
                message=f"Celery任务状态: {celery_status}",
                created_at="",
                updated_at=""
            )
        
        return TaskProgressResponse(
            task_id=progress.task_id,
            status=progress.status.value,
            stage=progress.stage.value,
            progress=progress.progress,
            message=progress.message,
            details=progress.details,
            error=progress.error,
            created_at=progress.created_at.isoformat(),
            updated_at=progress.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")

@router.get("/tasks/{task_id}/history")
async def get_task_history(task_id: str):
    """
    获取任务历史记录
    """
    try:
        history = await task_manager.get_task_history(task_id)
        
        return {
            "task_id": task_id,
            "history": history,
            "total_records": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务历史失败: {str(e)}")

@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务
    """
    try:
        await task_manager.cancel_task(task_id)
        
        return {
            "task_id": task_id,
            "message": "任务取消请求已发送",
            "status": "cancelled"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果
    """
    try:
        # 检查任务是否完成
        progress = await task_manager.get_task_progress(task_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if progress.status != TaskStatus.SUCCESS:
            raise HTTPException(
                status_code=400, 
                detail=f"任务尚未完成，当前状态: {progress.status.value}"
            )
        
        # 从Celery获取结果
        celery_result = AsyncResult(task_id, app=celery_app)
        
        if celery_result.ready():
            if celery_result.successful():
                return {
                    "task_id": task_id,
                    "status": "success",
                    "result": celery_result.result,
                    "progress": progress.details
                }
            else:
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(celery_result.result),
                    "progress": progress.details
                }
        else:
            raise HTTPException(status_code=400, detail="任务结果尚未准备就绪")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")

@router.get("/tasks")
async def list_active_tasks():
    """
    列出所有活动任务
    """
    try:
        # 获取Celery活动任务
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        # 获取WebSocket连接信息
        from app.api.v1.websockets import connection_manager
        connection_info = connection_manager.get_connection_info()
        
        return {
            "active_celery_tasks": active_tasks,
            "websocket_connections": connection_info,
            "total_active_tasks": len(connection_info.get("active_tasks", []))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.get("/tasks/stats")
async def get_task_stats():
    """
    获取任务统计信息
    """
    try:
        # 获取Celery统计信息
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        # 获取连接统计
        from app.api.v1.websockets import connection_manager
        connection_count = connection_manager.get_connection_count()
        
        return {
            "celery_stats": stats,
            "active_websocket_connections": connection_count,
            "system_status": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}") 