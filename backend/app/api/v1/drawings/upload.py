"""
图纸上传API模块 - 使用双重存储策略
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import tempfile
import logging
import uuid
from datetime import datetime
import time
from pathlib import Path

from ....database import get_db
from ....models.drawing import Drawing
from ....schemas.drawing import DrawingResponse
from ...deps import get_current_user
from ....models.user import User
from ....tasks import task_manager, TaskStatus, TaskStage, process_drawing_celery_task
from ....services.s3_service import s3_service

from io import BytesIO
from app.services.dual_storage_service import DualStorageService
from app.utils.file_utils import extract_file_type

logger = logging.getLogger(__name__)

# 创建上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter()

@router.post("/upload", response_model=Dict[str, Any])
async def upload_drawing(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传图纸文件 - 使用双重存储"""
    try:
        # 验证文件类型
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf', '.dwg')):
            raise HTTPException(
                status_code=400,
                detail="不支持的文件格式。支持：PNG, JPG, JPEG, PDF, DWG"
            )

        # 保存到本地临时文件
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{file.filename}"
        temp_path = UPLOAD_DIR / safe_filename
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 使用双重存储服务上传
        storage_service = DualStorageService()
        
        # 构造完整的 s3_key
        s3_key = f"drawings/{safe_filename}"
        
        upload_result = storage_service.upload_file_sync(
            file_obj=content,
            s3_key=s3_key,
            content_type=file.content_type or "application/octet-stream"
        )

        if not upload_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"文件上传失败: {upload_result.get('error')}"
            )

        # 提取文件类型
        file_type = extract_file_type(file.filename)

        # 创建数据库记录
        drawing = Drawing(
            filename=file.filename,
            file_path=str(temp_path),
            file_type=file_type,
            s3_key=upload_result.get("final_url"),
            file_size=len(content),
            user_id=current_user.id
        )
        
        db.add(drawing)
        db.commit()
        db.refresh(drawing)

        # 🔥 添加：创建任务并启动Celery处理
        task_id = str(uuid.uuid4())
        
        # 创建实时任务（同步方法，不需要await）
        task_manager.create_task(
            task_id=task_id,
            name=f"图纸处理：{file.filename}",
            user_id=current_user.id,
            metadata={
                "drawing_id": drawing.id,
                "file_name": file.filename,
                "operation": "full_process",
                "s3_key": upload_result.get("final_url")
            }
        )
        
        # 更新数据库中的task_id
        drawing.task_id = task_id
        db.commit()
        
        # 启动Celery任务
        celery_task = process_drawing_celery_task.delay(drawing.id, task_id)
        
        logger.info(f"✅ 图纸上传成功 - ID: {drawing.id}, Task ID: {task_id}, Celery Task: {celery_task.id}")
        logger.info(f"📋 存储方式: {upload_result.get('storage_method')}")

        return {
            "success": True,
            "message": "图纸上传成功，正在处理中...",
            "drawing_id": drawing.id,
            "task_id": task_id,
            "filename": file.filename,
            "storage_url": upload_result.get("final_url"),
            "storage_method": upload_result.get("storage_method")
        }

    except Exception as e:
        logger.error(f"图纸上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/upload/batch", response_model=Dict[str, Any])
async def upload_multiple_drawings(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量上传图纸 - 使用双重存储"""
    try:
        storage_service = DualStorageService()
        uploaded_drawings = []
        failed_uploads = []

        for i, file in enumerate(files):
            try:
                # 验证文件类型
                if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf', '.dwg')):
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": "不支持的文件格式"
                    })
                    continue

                # 保存到本地临时文件
                timestamp = int(time.time())
                safe_filename = f"{timestamp}_{i}_{file.filename}"
                temp_path = UPLOAD_DIR / safe_filename
                
                with open(temp_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)

                # 使用双重存储上传
                # 构造完整的 s3_key
                s3_key = f"drawings/{safe_filename}"
                
                upload_result = storage_service.upload_file_sync(
                    file_obj=content,
                    s3_key=s3_key,
                    content_type=file.content_type or "application/octet-stream"
                )

                if not upload_result.get("success"):
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": upload_result.get("error")
                    })
                    continue

                # 提取文件类型
                file_type = extract_file_type(file.filename)

                # 创建数据库记录
                drawing = Drawing(
                    filename=file.filename,
                    file_path=str(temp_path),
                    file_type=file_type,
                    s3_key=upload_result.get("final_url"),
                    file_size=len(content),
                    user_id=current_user.id
                )
                
                db.add(drawing)
                db.commit()
                db.refresh(drawing)

                # 🔥 添加：创建任务并启动Celery处理
                task_id = str(uuid.uuid4())
                
                # 创建实时任务（同步方法，不需要await）
                task_manager.create_task(
                    task_id=task_id,
                    name=f"图纸处理：{file.filename}",
                    user_id=current_user.id,
                    metadata={
                        "drawing_id": drawing.id,
                        "file_name": file.filename,
                        "operation": "full_process",
                        "s3_key": upload_result.get("final_url")
                    }
                )
                
                # 更新数据库中的task_id
                drawing.task_id = task_id
                db.commit()
                
                # 启动Celery任务
                celery_task = process_drawing_celery_task.delay(drawing.id, task_id)
                
                logger.info(f"✅ 批量上传图纸 - ID: {drawing.id}, Task ID: {task_id}, Celery Task: {celery_task.id}")

                uploaded_drawings.append({
                    "drawing_id": drawing.id,
                    "task_id": task_id,
                    "filename": file.filename,
                    "storage_url": upload_result.get("final_url"),
                    "storage_method": upload_result.get("storage_method")
                })

            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": str(e)
                })

        logger.info(f"✅ 批量上传完成 - 成功: {len(uploaded_drawings)}, 失败: {len(failed_uploads)}")

        return {
            "success": True,
            "message": f"批量上传完成 - 成功: {len(uploaded_drawings)}, 失败: {len(failed_uploads)}",
            "uploaded_drawings": uploaded_drawings,
            "failed_uploads": failed_uploads
        }

    except Exception as e:
        logger.error(f"批量上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")

# BackgroundTasks 相关函数已移除，现在统一使用 Celery 任务
# 所有图纸处理逻辑都在 drawing_tasks.py 中的 Celery 任务中实现 