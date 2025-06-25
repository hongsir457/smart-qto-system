"""
图纸列表和详情相关API
从原drawings.py中提取的列表查询功能
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging
import json
import httpx

from ....database import get_db
from ....models.drawing import Drawing
from ....schemas.drawing import DrawingStatus, OCRResultsResponse, AnalysisResultsResponse, ComponentsResponse
from ...deps import get_current_user
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

def _calculate_progress(status: str, processing_result: Dict[str, Any]) -> int:
    """计算处理进度百分比"""
    if status == "failed":
        return 0
    elif status == "completed":
        return 100
    elif status == "processing":
        # 处理processing_result可能是字符串的情况
        try:
            if isinstance(processing_result, str):
                processing_result = json.loads(processing_result)
            elif processing_result is None:
                processing_result = {}
            
            stages_completed = processing_result.get('stages_completed', [])
            total_stages = 4  # png_conversion, ocr_recognition, stage_one_analysis, stage_two_analysis
            return min(int((len(stages_completed) / total_stages) * 100), 95)
        except (json.JSONDecodeError, TypeError, AttributeError):
            return 10  # 默认给一个较低的进度值
    else:
        return 0

@router.get("/")
async def list_drawings(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图纸列表"""
    try:
        # 构建查询
        query = db.query(Drawing).filter(Drawing.user_id == current_user.id)
        
        # 根据状态过滤
        if status:
            query = query.filter(Drawing.status == status)
        
        # 先计算总数
        total = query.count()
        
        # 分页查询
        drawings = query.offset(skip).limit(limit).all()
        
        # 转换为响应格式
        drawings_data = []
        for drawing in drawings:
            # 安全处理processing_result
            try:
                if isinstance(drawing.processing_result, str):
                    processing_result = json.loads(drawing.processing_result)
                else:
                    processing_result = drawing.processing_result or {}
            except (json.JSONDecodeError, TypeError):
                processing_result = {}
            
            progress = _calculate_progress(drawing.status, processing_result)
            
            drawings_data.append({
                "id": drawing.id,
                "filename": drawing.filename,
                "status": drawing.status,
                "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
                "updated_at": drawing.updated_at.isoformat() if drawing.updated_at else None,
                "progress": progress,
                "file_size": drawing.file_size,
                "file_type": drawing.file_type,
                "file_path": drawing.file_path,
                "has_ocr_results": bool(drawing.ocr_results),
                "has_recognition_results": bool(drawing.recognition_results),
                "components_count": drawing.components_count or 0
            })
        
        return {
            "drawings": drawings_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"获取图纸列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图纸列表失败: {str(e)}")

@router.get("/{drawing_id}")
async def get_drawing(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个图纸详情"""
    try:
        # 查找图纸
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        # 计算进度 - 安全处理processing_result
        try:
            if isinstance(drawing.processing_result, str):
                processing_result = json.loads(drawing.processing_result)
            else:
                processing_result = drawing.processing_result or {}
        except (json.JSONDecodeError, TypeError):
            processing_result = {}
        
        progress = _calculate_progress(drawing.status, processing_result)
        
        # 返回详细信息
        return {
            "id": drawing.id,
            "filename": drawing.filename,
            "status": drawing.status,
            "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
            "updated_at": drawing.updated_at.isoformat() if drawing.updated_at else None,
            "progress": progress,
            "file_size": drawing.file_size,
            "file_type": drawing.file_type,
            "file_path": drawing.file_path,
            "processing_result": drawing.processing_result,
            "error_message": drawing.error_message,
            "ocr_results": drawing.ocr_results,
            "recognition_results": drawing.recognition_results,
            "ocr_recognition_display": drawing.ocr_recognition_display,
            "quantity_list_display": drawing.quantity_list_display,
            "components_count": drawing.components_count or 0,
            "task_id": drawing.task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图纸详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图纸详情失败: {str(e)}")

@router.get("/{drawing_id}/status", response_model=DrawingStatus)
async def get_drawing_status(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图纸处理状态"""
    try:
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        return DrawingStatus(
            id=drawing.id,
            filename=drawing.filename,
            status=drawing.status,
            progress=_calculate_progress(drawing.status, drawing.processing_result or {}),
            error_message=drawing.error_message,
            created_at=drawing.created_at,
            updated_at=drawing.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图纸状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图纸状态失败: {str(e)}")

@router.get("/{drawing_id}/ocr-results", response_model=OCRResultsResponse)
async def get_drawing_ocr_results(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图纸OCR识别结果"""
    try:
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.ocr_results:
            raise HTTPException(status_code=404, detail="OCR结果不存在，请先进行OCR识别")
        
        # 解析OCR结果
        try:
            if isinstance(drawing.ocr_results, str):
                ocr_data = json.loads(drawing.ocr_results)
            else:
                ocr_data = drawing.ocr_results
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=500, detail="OCR结果数据格式错误")
        
        return OCRResultsResponse(
            drawing_id=drawing.id,
            filename=drawing.filename,
            status=drawing.status,
            ocr_results=ocr_data,
            created_at=drawing.created_at,
            updated_at=drawing.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取OCR结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取OCR结果失败: {str(e)}")

@router.get("/{drawing_id}/analysis-results", response_model=AnalysisResultsResponse)
async def get_drawing_analysis_results(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图纸分析结果（结构化，兼容旧数据）"""
    try:
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.processing_result:
            raise HTTPException(status_code=404, detail="分析结果不存在，请先进行图纸处理")
        
        # 解析处理结果
        try:
            if isinstance(drawing.processing_result, str):
                processing_data = json.loads(drawing.processing_result)
            else:
                processing_data = drawing.processing_result
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=500, detail="分析结果数据格式错误")
        
        # 兼容字段补全
        def safe_get(key, default):
            return processing_data.get(key, default)
        
        return AnalysisResultsResponse(
            drawing_id=drawing.id,
            analysis_type=safe_get("analysis_type", "stage_two"),
            has_ai_analysis=safe_get("has_ai_analysis", False),
            components=safe_get("components", []),
            analysis_summary=safe_get("analysis_summary", {}),
            quality_assessment=safe_get("quality_assessment", {}),
            recommendations=safe_get("recommendations", []),
            statistics=safe_get("statistics", {}),
            llm_analysis=safe_get("llm_analysis", None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分析结果失败: {str(e)}")

@router.get("/{drawing_id}/components", response_model=ComponentsResponse)
async def get_drawing_components(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取图纸构件信息"""
    try:
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        # 从处理结果中提取构件信息
        components = []
        
        if drawing.processing_result:
            try:
                if isinstance(drawing.processing_result, str):
                    processing_data = json.loads(drawing.processing_result)
                else:
                    processing_data = drawing.processing_result
                
                components = processing_data.get('final_components', [])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"图纸 {drawing_id} 的处理结果格式错误")
        
        return ComponentsResponse(
            drawing_id=drawing.id,
            filename=drawing.filename,
            status=drawing.status,
            components=components,
            total_components=len(components),
            created_at=drawing.created_at,
            updated_at=drawing.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取构件信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取构件信息失败: {str(e)}")

@router.get("/{drawing_id}/s3-content/{content_type}")
async def get_s3_content(
    drawing_id: int,
    content_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    代理访问S3存储的内容（支持本地存储）
    content_type: result_b (JSON) 或 result_c (TXT)
    """
    try:
        # 获取图纸信息
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.processing_result:
            raise HTTPException(status_code=404, detail="未找到处理结果")
        
        # 获取S3 URL
        processing_result = drawing.processing_result
        if isinstance(processing_result, str):
            processing_result = json.loads(processing_result)
        
        s3_url = None
        if content_type == "result_b":
            s3_url = processing_result.get("result_b_corrected_json", {}).get("s3_url")
        elif content_type == "result_c":
            s3_url = processing_result.get("result_c_human_readable", {}).get("s3_url")
        else:
            raise HTTPException(status_code=400, detail="无效的内容类型")
        
        if not s3_url:
            raise HTTPException(status_code=404, detail="未找到S3链接")
        
        logger.info(f"代理访问内容: {s3_url}")
        
        # 检查是否为本地存储（file://开头）
        if s3_url.startswith("file://"):
            # 本地存储模式
            from pathlib import Path
            file_path = s3_url.replace("file://", "")
            local_file = Path(file_path)
            
            if not local_file.exists():
                raise HTTPException(status_code=404, detail="本地文件不存在")
            
            # 读取本地文件
            try:
                content = local_file.read_bytes()
                logger.info(f"✅ 成功读取本地文件: {local_file}")
                
                # 根据内容类型返回相应的响应
                if content_type == "result_b":
                    return Response(
                        content=content,
                        media_type="application/json",
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
                else:  # result_c
                    return Response(
                        content=content,
                        media_type="text/plain; charset=utf-8",
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
                    
            except Exception as e:
                logger.error(f"读取本地文件失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"读取本地文件失败: {str(e)}")
        
        else:
            # S3存储模式
            async with httpx.AsyncClient() as client:
                response = await client.get(s3_url, timeout=30.0)
                
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"S3访问失败: {response.status_code}")
                
                # 根据内容类型返回相应的响应
                if content_type == "result_b":
                    return Response(
                        content=response.content,
                        media_type="application/json",
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
                else:  # result_c
                    return Response(
                        content=response.content,
                        media_type="text/plain; charset=utf-8",
                        headers={"Cache-Control": "public, max-age=3600"}
                    )
                
    except httpx.RequestError as e:
        logger.error(f"S3代理请求失败: {str(e)}")
        raise HTTPException(status_code=502, detail=f"网络请求失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"代理访问失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}") 