#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision分析API端点
"""

import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import uuid
import tempfile

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.drawing import Drawing
from app.services.vision_analyzer import VisionAnalyzer
from app.services.s3_service import S3Service
from app.tasks.real_time_task_manager import RealTimeTaskManager, TaskStatus, TaskStage

logger = logging.getLogger(__name__)

router = APIRouter()

# 初始化服务
vision_analyzer = VisionAnalyzer()
s3_service = S3Service()
task_manager = RealTimeTaskManager()


@router.post("/analyze-image")
async def analyze_image_with_vision(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_preference: str = Form("both"),  # gpt4v, claude, both
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """直接使用Vision模型分析上传的图纸"""
    try:
        # 验证文件类型
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            raise HTTPException(
                status_code=400, 
                detail="只支持PNG、JPG、JPEG格式的图片文件"
            )
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建实时任务
        task_manager.create_task(
            task_id=task_id,
            name=f"vision_analysis:{file.filename}",
            user_id=current_user.id,
            metadata={
                "filename": file.filename,
                "model_preference": model_preference,
                "analysis_type": "direct_vision"
            }
        )
        
        # 保存临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_file_path = temp_file.name
        temp_file.close()
        
        # 保存上传的文件
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 添加后台任务
        background_tasks.add_task(
            process_vision_analysis_task,
            temp_file_path,
            task_id,
            current_user.id,
            file.filename,
            model_preference
        )
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "Vision分析任务已创建",
                "task_id": task_id,
                "status": "processing"
            }
        )
        
    except Exception as e:
        logger.error(f"创建Vision分析任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_vision_analysis_result(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取Vision分析结果"""
    try:
        # 从任务管理器获取任务状态
        task_info = task_manager.get_task(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task_info.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此任务")
        
        result = {
            "task_id": task_id,
            "status": task_info.status.value,
            "stage": task_info.stage.value,
            "progress": task_info.progress,
            "message": task_info.message,
            "created_at": task_info.created_at.isoformat(),
            "updated_at": task_info.updated_at.isoformat()
        }
        
        # 如果任务完成，添加结果数据
        if task_info.results:
            result["data"] = task_info.results
        
        if task_info.error_message:
            result["error"] = task_info.error_message
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Vision分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare/{drawing_id}")
async def compare_with_ocr_result(
    drawing_id: int,
    vision_task_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将Vision分析结果与OCR结果进行对比"""
    try:
        # 获取图纸记录
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        # 获取Vision分析结果
        vision_task = task_manager.get_task(vision_task_id)
        if not vision_task or vision_task.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Vision分析任务不存在")
        
        if vision_task.status != TaskStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Vision分析未完成或失败")
        
        # 获取OCR结果
        if not drawing.processing_result:
            raise HTTPException(status_code=400, detail="该图纸没有OCR分析结果")
        
        # 进行对比分析
        vision_result = vision_task.results
        ocr_result = drawing.processing_result
        
        comparison = vision_analyzer.compare_with_ocr_result(vision_result, ocr_result)
        
        # 保存对比结果到S3
        comparison_s3_key = f"comparisons/{drawing_id}/vision_vs_ocr_{vision_task_id}.json"
        comparison_url = vision_analyzer.save_result_to_s3(comparison, comparison_s3_key)
        
        return JSONResponse(content={
            "comparison": comparison,
            "s3_url": comparison_url,
            "drawing_id": drawing_id,
            "vision_task_id": vision_task_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对比分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drawings/{drawing_id}/vision-results")
async def get_drawing_vision_results(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定图纸的所有Vision分析结果"""
    try:
        # 验证图纸权限
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        # 获取用户的所有任务，筛选出与此图纸相关的Vision分析
        user_tasks = task_manager.get_user_tasks(current_user.id)
        
        vision_tasks = []
        for task in user_tasks:
            if (task.name.startswith("vision_analysis:") and 
                task.metadata.get("analysis_type") == "direct_vision"):
                vision_tasks.append({
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "filename": task.metadata.get("filename", ""),
                    "created_at": task.created_at.isoformat(),
                    "model_preference": task.metadata.get("model_preference", "both")
                })
        
        return JSONResponse(content={
            "drawing_id": drawing_id,
            "vision_analyses": vision_tasks
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Vision分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_vision_analysis_task(
    image_path: str, 
    task_id: str, 
    user_id: int, 
    filename: str, 
    model_preference: str
):
    """后台处理Vision分析任务"""
    logger.info(f"[{task_id}] 开始处理Vision分析后台任务。")
    logger.info(f"[{task_id}] 参数: image_path={image_path}, user_id={user_id}, filename={filename}, model_preference={model_preference}")

    try:
        # 更新任务状态
        await task_manager.update_task_status(
            task_id, 
            TaskStatus.PROCESSING, 
            TaskStage.INITIALIZING,
            progress=10, 
            message="开始Vision分析..."
        )
        
        # 执行Vision分析
        await task_manager.update_task_status(
            task_id, 
            TaskStatus.PROCESSING, 
            TaskStage.GPT_ANALYSIS,
            progress=30, 
            message="正在调用Vision模型分析图纸..."
        )
        
        logger.info(f"[{task_id}] 调用 vision_analyzer.analyze_image 开始...")
        result = vision_analyzer.analyze_image(
            image_path=image_path,
            task_id=task_id,
            model_preference=model_preference
        )
        logger.info(f"[{task_id}] 调用 vision_analyzer.analyze_image 完成。结果状态: {result.get('status')}")
        
        if result['status'] == 'success':
            # 任务成功完成
            logger.info(f"[{task_id}] 任务成功，更新状态为 SUCCESS。")
            await task_manager.update_task_status(
                task_id, 
                TaskStatus.SUCCESS, 
                TaskStage.COMPLETED,
                progress=100, 
                message="Vision分析完成",
                results=result['data']
            )
        else:
            # 任务失败
            error_details = result.get('error', '未知错误')
            logger.error(f"[{task_id}] 任务失败，更新状态为 FAILURE。错误详情: {error_details}")
            logger.error(f"[{task_id}] 完整失败响应: {result}")
            await task_manager.update_task_status(
                task_id, 
                TaskStatus.FAILURE, 
                TaskStage.FAILED,
                progress=0, 
                message="Vision分析失败",
                error_message=str(error_details)
            )
        
    except Exception as e:
        logger.error(f"[{task_id}] Vision分析任务处理过程中发生未捕获异常: {e}", exc_info=True)
        await task_manager.update_task_status(
            task_id, 
            TaskStatus.FAILURE, 
            TaskStage.FAILED,
            progress=0, 
            message="Vision分析任务失败",
            error_message=str(e)
        )
    
    finally:
        # 清理临时文件
        try:
            if os.path.exists(image_path):
                os.unlink(image_path)
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件失败: {cleanup_error}")


@router.get("/models/status")
async def get_vision_models_status():
    """获取Vision模型可用状态"""
    try:
        status = {
            "gpt4v": {
                "available": bool(os.getenv("OPENAI_API_KEY")),
                "model": "gpt-4o",
                "description": "OpenAI GPT-4 with Vision"
            },
            "claude": {
                "available": bool(os.getenv("ANTHROPIC_API_KEY")),
                "model": "claude-3-5-sonnet-20241022",
                "description": "Anthropic Claude 3.5 Sonnet"
            }
        }
        
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"获取模型状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 