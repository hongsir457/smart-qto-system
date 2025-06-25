#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vision切片分析API端点
提供OpenAI Vision + 智能切片的图像分析服务
"""

import logging
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
import aiofiles

from app.api.deps import get_current_user
from app.services.openai_vision_slicer import OpenAIVisionSlicer
from app.tasks.real_time_task_manager import RealTimeTaskManager
from app.schemas.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

# 初始化服务
vision_slicer = OpenAIVisionSlicer()
task_manager = RealTimeTaskManager()

@router.post("/analyze-with-slicing")
async def analyze_image_with_slicing(
    file: UploadFile = File(..., description="图纸图像文件"),
    analysis_type: str = Form("default", description="分析类型"),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    使用智能切片进行图像Vision分析
    
    Args:
        file: 上传的图像文件
        analysis_type: 分析类型
        current_user: 当前用户
        
    Returns:
        分析结果
    """
    task_id = f"vision_slice_{current_user.id}_{int(time.time())}"
    
    try:
        # 验证文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图像文件")
        
        # 创建任务
        await task_manager.create_task(
            task_id=task_id,
            user_id=current_user.id,
            task_type="vision_slice_analysis",
            status="processing",
            metadata={
                "filename": file.filename,
                "analysis_type": analysis_type,
                "file_size": file.size
            }
        )
        
        # 保存上传文件到临时目录
        temp_dir = Path(tempfile.gettempdir()) / "vision_slice"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file_path = temp_dir / f"{task_id}_{file.filename}"
        
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"开始Vision切片分析 - 任务ID: {task_id}, 文件: {file.filename}")
        
        # 更新任务状态
        await task_manager.update_task(
            task_id=task_id,
            status="slicing",
            progress=10,
            message="开始图像切片处理..."
        )
        
        # 执行切片分析
        try:
            analysis_result = await vision_slicer.analyze_image_with_slicing(
                str(temp_file_path), 
                task_id,
                _get_analysis_prompt(analysis_type)
            )
            
            # 更新任务状态
            await task_manager.update_task(
                task_id=task_id,
                status="completed",
                progress=100,
                message="Vision切片分析完成",
                result=analysis_result
            )
            
            # 清理临时文件
            try:
                temp_file_path.unlink()
            except:
                pass
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "task_id": task_id,
                    "message": "Vision切片分析完成",
                    "data": analysis_result
                }
            )
            
        except Exception as analysis_error:
            # 分析失败
            await task_manager.update_task(
                task_id=task_id,
                status="failed",
                progress=0,
                message=f"Vision分析失败: {str(analysis_error)}"
            )
            
            # 清理临时文件
            try:
                temp_file_path.unlink()
            except:
                pass
            
            raise HTTPException(
                status_code=500, 
                detail=f"Vision分析失败: {str(analysis_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision切片分析异常: {e}")
        
        # 更新任务状态
        try:
            await task_manager.update_task(
                task_id=task_id,
                status="failed",
                progress=0,
                message=f"系统异常: {str(e)}"
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"系统异常: {str(e)}")

@router.post("/analyze-direct")
async def analyze_image_direct(
    file: UploadFile = File(..., description="图纸图像文件"),
    analysis_type: str = Form("default", description="分析类型"),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    直接进行图像Vision分析（不切片，用于对比）
    
    Args:
        file: 上传的图像文件
        analysis_type: 分析类型
        current_user: 当前用户
        
    Returns:
        分析结果
    """
    task_id = f"vision_direct_{current_user.id}_{int(time.time())}"
    
    try:
        # 验证文件类型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只支持图像文件")
        
        # 创建任务
        await task_manager.create_task(
            task_id=task_id,
            user_id=current_user.id,
            task_type="vision_direct_analysis",
            status="processing",
            metadata={
                "filename": file.filename,
                "analysis_type": analysis_type,
                "file_size": file.size
            }
        )
        
        # 保存上传文件到临时目录
        temp_dir = Path(tempfile.gettempdir()) / "vision_direct"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file_path = temp_dir / f"{task_id}_{file.filename}"
        
        async with aiofiles.open(temp_file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"开始直接Vision分析 - 任务ID: {task_id}, 文件: {file.filename}")
        
        # 更新任务状态
        await task_manager.update_task(
            task_id=task_id,
            status="analyzing",
            progress=50,
            message="正在进行Vision分析..."
        )
        
        # 执行直接分析
        try:
            analysis_result = await vision_slicer.analyze_full_image_direct(
                str(temp_file_path), 
                task_id,
                _get_analysis_prompt(analysis_type)
            )
            
            # 更新任务状态
            await task_manager.update_task(
                task_id=task_id,
                status="completed",
                progress=100,
                message="直接Vision分析完成",
                result=analysis_result
            )
            
            # 清理临时文件
            try:
                temp_file_path.unlink()
            except:
                pass
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "task_id": task_id,
                    "message": "直接Vision分析完成",
                    "data": analysis_result
                }
            )
            
        except Exception as analysis_error:
            # 分析失败
            await task_manager.update_task(
                task_id=task_id,
                status="failed",
                progress=0,
                message=f"Vision分析失败: {str(analysis_error)}"
            )
            
            # 清理临时文件
            try:
                temp_file_path.unlink()
            except:
                pass
            
            raise HTTPException(
                status_code=500, 
                detail=f"Vision分析失败: {str(analysis_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"直接Vision分析异常: {e}")
        
        # 更新任务状态
        try:
            await task_manager.update_task(
                task_id=task_id,
                status="failed",
                progress=0,
                message=f"系统异常: {str(e)}"
            )
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"系统异常: {str(e)}")

@router.get("/slice-info/{task_id}")
async def get_slice_info(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    获取切片信息
    
    Args:
        task_id: 任务ID
        current_user: 当前用户
        
    Returns:
        切片信息
    """
    try:
        # 获取任务信息
        task_info = await task_manager.get_task(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 验证用户权限
        if task_info.get('user_id') != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问此任务")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "task_id": task_id,
                "data": task_info
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取切片信息异常: {e}")
        raise HTTPException(status_code=500, detail=f"系统异常: {str(e)}")

@router.get("/compare-methods")
async def compare_analysis_methods(
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    获取分析方法对比信息
    
    Returns:
        对比信息
    """
    comparison_info = {
        "methods": {
            "direct_analysis": {
                "name": "直接分析",
                "description": "直接将图像发送给OpenAI Vision API",
                "pros": [
                    "处理速度快",
                    "实现简单",
                    "适合小尺寸图像"
                ],
                "cons": [
                    "大图像会被自动压缩",
                    "可能丢失细节信息",
                    "受API分辨率限制"
                ],
                "best_for": "2048x2048以下的图像"
            },
            "slice_analysis": {
                "name": "智能切片分析",
                "description": "将大图像切片后分别分析，再合并结果",
                "pros": [
                    "保持原始分辨率",
                    "不丢失细节信息",
                    "适合超大图像",
                    "智能重叠区域处理"
                ],
                "cons": [
                    "处理时间较长",
                    "消耗更多API调用",
                    "实现复杂度高"
                ],
                "best_for": "2048x2048以上的高分辨率图像"
            }
        },
        "recommendations": {
            "small_images": "使用直接分析方法",
            "large_images": "使用智能切片分析方法",
            "high_detail_required": "推荐使用切片分析",
            "speed_priority": "推荐使用直接分析"
        },
        "technical_specs": {
            "max_resolution_direct": "2048x2048 (自动压缩)",
            "max_resolution_slice": "无限制 (智能切片)",
            "slice_overlap": "10% (可配置)",
            "slice_size": "2048x2048",
            "supported_formats": ["PNG", "JPEG", "WebP", "GIF"]
        }
    }
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": comparison_info
        }
    )

def _get_analysis_prompt(analysis_type: str) -> str:
    """
    根据分析类型获取提示词
    
    Args:
        analysis_type: 分析类型
        
    Returns:
        分析提示词
    """
    prompts = {
        "default": """你是一个专业的建筑图纸分析专家。请分析提供的建筑图纸，识别其中的建筑构件。

请按照以下JSON格式返回分析结果：

```json
{
    "components": [
        {
            "id": "构件唯一标识",
            "type": "构件类型(column/beam/slab/wall/foundation/stair等)",
            "name": "构件名称",
            "bbox": [x1, y1, x2, y2],
            "center": [x, y],
            "confidence": 0.95,
            "properties": {
                "material": "材料",
                "size": "尺寸信息",
                "annotation": "标注信息"
            },
            "dimensions": {
                "length": "长度",
                "width": "宽度", 
                "height": "高度"
            }
        }
    ],
    "confidence_score": 0.92,
    "summary": "分析摘要",
    "detected_elements": ["检测到的元素列表"],
    "quality": {
        "image_clarity": "图像清晰度评估",
        "annotation_completeness": "标注完整性"
    }
}
```

重点关注：
1. 准确识别构件类型和位置
2. 提取尺寸和材料信息
3. 识别图纸标注和文字
4. 评估识别置信度""",

        "structural": """你是结构工程师，专门分析结构图纸。请重点识别：
1. 结构构件（柱、梁、板、墙、基础）
2. 钢筋配置信息
3. 混凝土强度等级
4. 构件尺寸和规格
5. 结构连接节点

按照标准JSON格式返回结构化分析结果。""",

        "architectural": """你是建筑师，专门分析建筑图纸。请重点识别：
1. 建筑空间布局
2. 门窗位置和规格
3. 墙体类型和厚度
4. 房间功能标注
5. 建筑尺寸标注

按照标准JSON格式返回建筑分析结果。""",

        "mep": """你是机电工程师，专门分析机电图纸。请重点识别：
1. 机电设备位置
2. 管线走向和规格
3. 电气设备和线路
4. 给排水系统
5. 暖通空调系统

按照标准JSON格式返回机电分析结果。"""
    }
    
    return prompts.get(analysis_type, prompts["default"]) 