"""
结果导出相关API
从原drawings.py中提取的导出功能
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import logging
import json
import tempfile
import os

from ....database import get_db
from ....models.drawing import Drawing
from ...deps import get_current_user
from ....models.user import User
from .processor import get_processor
from ....services.export_service import export_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{drawing_id}/export/excel")
async def export_drawing_excel(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出图纸分析结果为Excel文件
    """
    try:
        # 查找图纸
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.processing_result:
            raise HTTPException(status_code=404, detail="该图纸尚未处理完成，无法导出")
        
        # 解析处理结果
        try:
            if isinstance(drawing.processing_result, str):
                processing_data = json.loads(drawing.processing_result)
            else:
                processing_data = drawing.processing_result
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=500, detail="处理结果数据格式错误")
        
        # 创建临时Excel文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
            temp_path = temp_file.name
        
        # 使用处理器导出Excel
        processor = get_processor()
        success = processor.export_components_to_excel(processing_data, temp_path)
        
        if not success:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail="Excel导出失败")
        
        # 生成文件名
        safe_filename = drawing.filename.replace('.', '_')
        excel_filename = f"{safe_filename}_构件清单.xlsx"
        
        # 返回文件，设置删除回调
        def cleanup():
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"清理临时Excel文件失败: {e}")
        
        response = FileResponse(
            path=temp_path,
            filename=excel_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # 注册清理回调（注意：实际生产环境中可能需要更复杂的清理机制）
        response.background = cleanup
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出Excel失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.get("/{drawing_id}/export/json")
async def export_drawing_json(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出图纸分析结果为JSON文件
    """
    try:
        # 查找图纸
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.processing_result:
            raise HTTPException(status_code=404, detail="该图纸尚未处理完成，无法导出")
        
        # 解析处理结果
        try:
            if isinstance(drawing.processing_result, str):
                processing_data = json.loads(drawing.processing_result)
            else:
                processing_data = drawing.processing_result
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=500, detail="处理结果数据格式错误")
        
        # 创建导出数据结构
        export_data = {
            "drawing_info": {
                "id": drawing.id,
                "filename": drawing.filename,
                "status": drawing.status,
                "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
                "updated_at": drawing.updated_at.isoformat() if drawing.updated_at else None
            },
            "processing_result": processing_data,
            "export_timestamp": "2025-06-08T15:30:00",
            "export_version": "1.0"
        }
        
        # 创建临时JSON文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as temp_file:
            json.dump(export_data, temp_file, ensure_ascii=False, indent=2)
            temp_path = temp_file.name
        
        # 生成文件名
        safe_filename = drawing.filename.replace('.', '_')
        json_filename = f"{safe_filename}_分析结果.json"
        
        # 返回文件
        def cleanup():
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"清理临时JSON文件失败: {e}")
        
        response = FileResponse(
            path=temp_path,
            filename=json_filename,
            media_type='application/json'
        )
        
        response.background = cleanup
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出JSON失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@router.get("/{drawing_id}/export/pdf-report")
async def export_drawing_pdf_report(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出图纸分析报告为PDF文件
    """
    try:
        # 查找图纸
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.processing_result:
            raise HTTPException(status_code=404, detail="该图纸尚未处理完成，无法导出")
        
        # 解析处理结果
        try:
            if isinstance(drawing.processing_result, str):
                processing_data = json.loads(drawing.processing_result)
            else:
                processing_data = drawing.processing_result
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=500, detail="处理结果数据格式错误")
        
        # 模拟PDF报告生成（实际项目中需要实现真正的PDF生成逻辑）
        # 这里暂时返回一个模拟的PDF文件提示
        raise HTTPException(
            status_code=501, 
            detail="PDF报告导出功能正在开发中，请使用Excel或JSON导出"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出PDF报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}") 

@router.get("/{drawing_id}/export")
async def export_drawing_quantities(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    导出图纸工程量到Excel文件
    
    Args:
        drawing_id: 图纸ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        FileResponse: Excel文件下载响应
    """
    try:
        logger.info(f"📊 用户 {current_user.id} 请求导出图纸 {drawing_id} 的工程量")
        
        # 获取图纸记录
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(
                status_code=404, 
                detail="图纸不存在或无权限访问"
            )
        
        # 检查图纸状态
        if drawing.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"图纸处理未完成，当前状态: {drawing.status}"
            )
        
        # 检查是否有工程量数据
        if not drawing.quantity_results:
            raise HTTPException(
                status_code=400,
                detail="图纸无工程量计算结果，无法导出"
            )
        
        # 准备导出数据
        drawing_data = {
            'id': drawing.id,
            'filename': drawing.filename,
            'quantity_results': drawing.quantity_results,
            'recognition_results': drawing.recognition_results,
            'components_count': drawing.components_count,
            'created_at': drawing.created_at.strftime('%Y-%m-%d %H:%M:%S') if drawing.created_at else '',
            'updated_at': drawing.updated_at.strftime('%Y-%m-%d %H:%M:%S') if drawing.updated_at else ''
        }
        
        # 导出到Excel
        excel_path = export_service.export_quantities_to_excel(drawing_data)
        
        if not excel_path or not os.path.exists(excel_path):
            raise HTTPException(
                status_code=500,
                detail="Excel文件生成失败"
            )
        
        # 生成下载文件名
        safe_filename = drawing.filename.replace(' ', '_') if drawing.filename else 'drawing'
        if '.' in safe_filename:
            safe_filename = safe_filename.rsplit('.', 1)[0]
        
        download_filename = f"工程量计算_{safe_filename}.xlsx"
        
        logger.info(f"✅ 工程量导出成功: {excel_path}")
        
        # 返回文件下载响应
        return FileResponse(
            path=excel_path,
            filename=download_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{download_filename}"
            }
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"❌ 导出工程量失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"导出失败: {str(e)}"
        )

@router.get("/{drawing_id}/export/preview")
async def preview_export_data(
    drawing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预览导出数据（不生成文件）
    
    Args:
        drawing_id: 图纸ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        Dict: 工程量数据预览
    """
    try:
        logger.info(f"👀 用户 {current_user.id} 预览图纸 {drawing_id} 的导出数据")
        
        # 获取图纸记录
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(
                status_code=404, 
                detail="图纸不存在或无权限访问"
            )
        
        # 检查图纸状态
        if drawing.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"图纸处理未完成，当前状态: {drawing.status}"
            )
        
        # 返回工程量数据
        quantity_results = drawing.quantity_results or {}
        
        return {
            "drawing_info": {
                "id": drawing.id,
                "filename": drawing.filename,
                "status": drawing.status,
                "components_count": drawing.components_count,
                "created_at": drawing.created_at,
                "updated_at": drawing.updated_at
            },
            "quantity_summary": quantity_results.get('total_summary', {}),
            "quantities_by_type": quantity_results.get('quantities', {}),
            "component_types_found": quantity_results.get('component_types_found', []),
            "calculation_time": quantity_results.get('calculation_time', ''),
            "exportable": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 预览导出数据失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"预览失败: {str(e)}"
        )