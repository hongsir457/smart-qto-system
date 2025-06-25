#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能切片OCR API端点
提供PaddleOCR + 智能切片的OCR处理服务
"""

import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_current_active_user
from app.models.user import User
from app.services.ocr.paddle_ocr_service import PaddleOCRService
from app.services.ocr.paddle_ocr_with_slicing import PaddleOCRWithSlicing

router = APIRouter()
logger = logging.getLogger(__name__)

# 初始化服务
ocr_service = PaddleOCRService()
slicing_ocr_service = PaddleOCRWithSlicing()

async def save_upload_file(upload_file: UploadFile) -> str:
    """保存上传文件到临时目录"""
    suffix = Path(upload_file.filename).suffix if upload_file.filename else '.png'
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        content = await upload_file.read()
        tmp_file.write(content)
        return tmp_file.name

def cleanup_temp_file(file_path: str):
    """清理临时文件"""
    try:
        Path(file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")

@router.post("/analyze")
async def analyze_with_smart_slicing(
    file: UploadFile = File(...),
    force_slicing: Optional[bool] = Query(None, description="强制使用切片（None=自动判断）"),
    current_user: User = Depends(get_current_active_user)
):
    """
    智能切片OCR分析
    自动判断是否使用切片，提供最佳OCR效果
    """
    task_id = f"ocr_slice_{uuid.uuid4().hex[:8]}"
    temp_path = None
    
    try:
        logger.info(f"开始智能切片OCR分析 - 任务ID: {task_id}, 用户: {current_user.username}")
        
        # 保存上传文件
        temp_path = await save_upload_file(file)
        logger.info(f"文件已保存: {temp_path}")
        
        # 执行OCR分析
        result = await ocr_service.process_image_async(
            image_path=temp_path,
            use_slicing=force_slicing
        )
        
        # 构建响应
        response = {
            "success": result.get('success', False),
            "task_id": task_id,
            "file_name": file.filename,
            "processing_method": result.get('processing_method', 'unknown'),
            "ocr_result": {
                "total_text_regions": result.get('statistics', {}).get('total_regions', 0),
                "avg_confidence": result.get('statistics', {}).get('avg_confidence', 0),
                "processing_time": result.get('statistics', {}).get('processing_time', 0),
                "text_regions": result.get('text_regions', []),
                "all_text": result.get('all_text', '')
            },
            "slicing_info": result.get('slicing_info', {}),
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加处理摘要
        if 'processing_summary' in result:
            response['processing_summary'] = result['processing_summary']
        
        logger.info(f"智能切片OCR完成 - {task_id}, 识别区域: {response['ocr_result']['total_text_regions']}")
        
        return response
        
    except Exception as e:
        logger.error(f"智能切片OCR失败 - {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)

@router.post("/analyze-with-forced-slicing")
async def analyze_with_forced_slicing(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    强制使用切片OCR分析
    适用于大图像或需要最高精度的场景
    """
    task_id = f"ocr_forced_slice_{uuid.uuid4().hex[:8]}"
    temp_path = None
    
    try:
        logger.info(f"开始强制切片OCR分析 - 任务ID: {task_id}")
        
        # 保存上传文件
        temp_path = await save_upload_file(file)
        
        # 执行强制切片OCR
        result = await ocr_service.process_with_slicing_forced(
            image_path=temp_path,
            task_id=task_id
        )
        
        response = {
            "success": result.get('success', False),
            "task_id": task_id,
            "file_name": file.filename,
            "processing_method": "forced_slicing_ocr",
            "ocr_result": {
                "total_text_regions": result.get('statistics', {}).get('total_regions', 0),
                "avg_confidence": result.get('statistics', {}).get('avg_confidence', 0),
                "processing_time": result.get('statistics', {}).get('processing_time', 0),
                "text_regions": result.get('text_regions', []),
                "all_text": result.get('all_text', '')
            },
            "slicing_info": result.get('slicing_info', {}),
            "processing_summary": result.get('processing_summary', {}),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"强制切片OCR完成 - {task_id}")
        return response
        
    except Exception as e:
        logger.error(f"强制切片OCR失败 - {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)

@router.post("/compare-methods")
async def compare_ocr_methods(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    比较直接OCR和切片OCR的效果
    用于性能分析和方法选择
    """
    task_id = f"ocr_compare_{uuid.uuid4().hex[:8]}"
    temp_path = None
    
    try:
        logger.info(f"开始OCR方法比较 - 任务ID: {task_id}")
        
        # 保存上传文件
        temp_path = await save_upload_file(file)
        
        # 执行方法比较
        comparison_result = await ocr_service.compare_methods(temp_path)
        
        response = {
            "success": True,
            "task_id": task_id,
            "file_name": file.filename,
            "comparison_result": comparison_result,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"OCR方法比较完成 - {task_id}")
        return response
        
    except Exception as e:
        logger.error(f"OCR方法比较失败 - {task_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)

@router.get("/service-status")
async def get_ocr_service_status(
    current_user: User = Depends(get_current_active_user)
):
    """获取OCR服务状态"""
    
    try:
        status = {
            "enhanced_ocr_service": ocr_service.get_status(),
            "slicing_ocr_service": {
                "available": slicing_ocr_service.is_available(),
                "intelligent_slicer": slicing_ocr_service.image_slicer.is_available(),
                "original_ocr": slicing_ocr_service.ocr_service.is_available(),
                "storage": slicing_ocr_service.storage is not None
            },
            "overall_status": {
                "enhanced_service_available": ocr_service.is_available(),
                "slicing_service_available": slicing_ocr_service.is_available(),
                "all_services_ready": ocr_service.is_available() and slicing_ocr_service.is_available()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"获取OCR服务状态失败: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.post("/configure")
async def configure_ocr_service(
    auto_slicing: Optional[bool] = Query(None, description="是否启用自动切片"),
    slice_threshold: Optional[int] = Query(None, description="切片阈值（像素）"),
    current_user: User = Depends(get_current_active_user)
):
    """配置OCR服务参数"""
    
    try:
        changes = {}
        
        if auto_slicing is not None:
            ocr_service.set_auto_slicing(auto_slicing)
            changes['auto_slicing'] = auto_slicing
        
        if slice_threshold is not None:
            ocr_service.set_slice_threshold(slice_threshold)
            changes['slice_threshold'] = slice_threshold
        
        response = {
            "success": True,
            "message": "OCR服务配置已更新",
            "changes": changes,
            "current_config": {
                "auto_slicing": ocr_service.auto_slicing,
                "slice_threshold": ocr_service.slice_threshold
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"OCR服务配置更新: {changes}")
        return response
        
    except Exception as e:
        logger.error(f"配置OCR服务失败: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/slice-info/{task_id}")
async def get_slice_info(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取切片处理信息（如果有的话）"""
    
    try:
        # 这里可以从存储中获取切片信息
        # 目前返回基本信息
        
        response = {
            "task_id": task_id,
            "message": "切片信息查询功能",
            "note": "具体的切片信息需要在处理过程中存储",
            "timestamp": datetime.now().isoformat()
        }
        
        return response
        
    except Exception as e:
        logger.error(f"获取切片信息失败: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        ) 