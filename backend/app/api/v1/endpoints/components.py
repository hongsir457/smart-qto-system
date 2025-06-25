"""
构件管理路由模块
提供构件CRUD、批量操作、模板管理等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from ....database import get_db
from ....models.drawing import Drawing
from ...deps import get_current_user
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/")
async def list_components(
    drawing_id: Optional[int] = Query(None, description="图纸ID"),
    component_type: Optional[str] = Query(None, description="构件类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取构件列表
    支持按图纸ID、构件类型过滤，支持分页
    """
    try:
        # 构建基础查询 - 从图纸的processing_result中提取构件信息
        query = db.query(Drawing).filter(Drawing.user_id == current_user.id)
        
        if drawing_id:
            query = query.filter(Drawing.id == drawing_id)
        
        drawings = query.offset((page - 1) * page_size).limit(page_size).all()
        
        components = []
        for drawing in drawings:
            if drawing.processing_result:
                try:
                    import json
                    if isinstance(drawing.processing_result, str):
                        result = json.loads(drawing.processing_result)
                    else:
                        result = drawing.processing_result
                    
                    # 提取构件信息
                    drawing_components = result.get('final_components', [])
                    for comp in drawing_components:
                        if not component_type or comp.get('type') == component_type:
                            components.append({
                                'id': comp.get('id', f"{drawing.id}_{comp.get('code', 'unknown')}"),
                                'drawing_id': drawing.id,
                                'drawing_name': drawing.filename,
                                'code': comp.get('code'),
                                'type': comp.get('type'),
                                'dimensions': comp.get('dimensions'),
                                'material': comp.get('material'),
                                'quantity': comp.get('quantity', 1),
                                'unit': comp.get('unit'),
                                'volume': comp.get('volume'),
                                'area': comp.get('area'),
                                'length': comp.get('length'),
                                'created_at': drawing.created_at.isoformat() if drawing.created_at else None
                            })
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"解析图纸 {drawing.id} 构件数据失败: {e}")
                    continue
        
        total = len(components)
        
        return {
            "success": True,  
            "data": {
                "components": components,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            },
            "message": f"成功获取 {len(components)} 个构件"
        }
        
    except Exception as e:
        logger.error(f"获取构件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取构件列表失败: {str(e)}")

@router.get("/{component_id}")
async def get_component(
    component_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取构件详情"""
    try:
        # 解析component_id (格式: drawing_id_component_code)
        parts = component_id.split('_', 1)
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="无效的构件ID格式")
        
        drawing_id = int(parts[0])
        component_code = parts[1]
        
        # 查找图纸
        drawing = db.query(Drawing).filter(
            Drawing.id == drawing_id,
            Drawing.user_id == current_user.id
        ).first()
        
        if not drawing:
            raise HTTPException(status_code=404, detail="图纸不存在")
        
        if not drawing.processing_result:
            raise HTTPException(status_code=404, detail="图纸未处理完成")
        
        # 查找构件
        import json
        if isinstance(drawing.processing_result, str):
            result = json.loads(drawing.processing_result)
        else:
            result = drawing.processing_result
        
        components = result.get('final_components', [])
        component = None
        for comp in components:
            if comp.get('code') == component_code:
                component = comp
                break
        
        if not component:
            raise HTTPException(status_code=404, detail="构件不存在")
        
        # 增强构件详情信息
        component_detail = {
            'id': component_id,
            'drawing_id': drawing_id,
            'drawing_name': drawing.filename,
            'code': component.get('code'),
            'type': component.get('type'),
            'dimensions': component.get('dimensions'),
            'material': component.get('material'),
            'quantity': component.get('quantity', 1),
            'unit': component.get('unit'),
            'volume': component.get('volume'),
            'area': component.get('area'),
            'length': component.get('length'),
            'specifications': component.get('specifications', {}),
            'location': component.get('location'),
            'notes': component.get('notes'),
            'created_at': drawing.created_at.isoformat() if drawing.created_at else None,
            'updated_at': drawing.updated_at.isoformat() if drawing.updated_at else None
        }
        
        return {
            "success": True,
            "data": component_detail,
            "message": "成功获取构件详情"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取构件详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取构件详情失败: {str(e)}")

@router.post("/batch-update")
async def batch_update_components(
    updates: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量更新构件
    支持批量修改构件属性
    """
    try:
        updated_count = 0
        errors = []
        
        for update_data in updates:
            try:
                component_id = update_data.get('id')
                if not component_id:
                    errors.append("缺少构件ID")
                    continue
                
                # 解析component_id
                parts = component_id.split('_', 1)
                if len(parts) < 2:
                    errors.append(f"无效的构件ID格式: {component_id}")
                    continue
                
                drawing_id = int(parts[0])
                component_code = parts[1]
                
                # 查找并更新图纸中的构件数据
                drawing = db.query(Drawing).filter(
                    Drawing.id == drawing_id,
                    Drawing.user_id == current_user.id
                ).first()
                
                if not drawing:
                    errors.append(f"图纸不存在: {drawing_id}")
                    continue
                
                if drawing.processing_result:
                    import json
                    if isinstance(drawing.processing_result, str):
                        result = json.loads(drawing.processing_result)
                    else:
                        result = drawing.processing_result
                    
                    components = result.get('final_components', [])
                    
                    # 更新构件数据
                    for comp in components:
                        if comp.get('code') == component_code:
                            # 更新允许修改的字段
                            updatable_fields = ['quantity', 'material', 'specifications', 'notes', 'unit']
                            for field in updatable_fields:
                                if field in update_data:
                                    comp[field] = update_data[field]
                            
                            updated_count += 1
                            break
                    
                    # 保存更新
                    result['final_components'] = components
                    drawing.processing_result = result
                    db.commit()
                
            except Exception as e:
                errors.append(f"更新构件 {component_id} 失败: {str(e)}")
                continue
        
        return {
            "success": True,
            "data": {
                "updated_count": updated_count,
                "errors": errors
            },
            "message": f"成功更新 {updated_count} 个构件"
        }
        
    except Exception as e:
        logger.error(f"批量更新构件失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新构件失败: {str(e)}")

@router.get("/templates")
async def get_component_templates(
    component_type: Optional[str] = Query(None, description="构件类型")
):
    """获取构件模板"""
    try:
        templates = {
            "beam": {
                "name": "梁构件模板",
                "fields": {
                    "code": {"type": "string", "required": True, "description": "构件编号"},
                    "dimensions": {"type": "string", "required": True, "description": "截面尺寸", "example": "300×600"},
                    "length": {"type": "number", "required": True, "description": "长度(mm)"},
                    "material": {"type": "string", "required": True, "description": "材料", "default": "C30混凝土"},
                    "quantity": {"type": "integer", "required": True, "description": "数量", "default": 1},
                    "unit": {"type": "string", "required": True, "description": "单位", "default": "根"}
                },
                "calculation_rules": {
                    "volume": "width * height * length / 1000000000",  # 立方米
                    "area": "2 * (width + height) * length / 1000000"   # 平方米
                }
            },
            "column": {
                "name": "柱构件模板", 
                "fields": {
                    "code": {"type": "string", "required": True, "description": "构件编号"},
                    "dimensions": {"type": "string", "required": True, "description": "截面尺寸", "example": "400×400"},
                    "height": {"type": "number", "required": True, "description": "高度(mm)"},
                    "material": {"type": "string", "required": True, "description": "材料", "default": "C30混凝土"},
                    "quantity": {"type": "integer", "required": True, "description": "数量", "default": 1},
                    "unit": {"type": "string", "required": True, "description": "单位", "default": "根"}
                },
                "calculation_rules": {
                    "volume": "width * depth * height / 1000000000",
                    "area": "2 * (width + depth) * height / 1000000"
                }
            },
            "wall": {
                "name": "墙构件模板",
                "fields": {
                    "code": {"type": "string", "required": True, "description": "构件编号"},
                    "thickness": {"type": "number", "required": True, "description": "厚度(mm)", "example": 200},
                    "length": {"type": "number", "required": True, "description": "长度(mm)"},
                    "height": {"type": "number", "required": True, "description": "高度(mm)"},
                    "material": {"type": "string", "required": True, "description": "材料", "default": "C30混凝土"},
                    "quantity": {"type": "integer", "required": True, "description": "数量", "default": 1},
                    "unit": {"type": "string", "required": True, "description": "单位", "default": "面"}
                },
                "calculation_rules": {
                    "volume": "thickness * length * height / 1000000000",
                    "area": "length * height / 1000000"
                }
            },
            "slab": {
                "name": "板构件模板",
                "fields": {
                    "code": {"type": "string", "required": True, "description": "构件编号"},
                    "thickness": {"type": "number", "required": True, "description": "厚度(mm)", "example": 120},
                    "area": {"type": "number", "required": True, "description": "面积(m²)"},
                    "material": {"type": "string", "required": True, "description": "材料", "default": "C30混凝土"},
                    "quantity": {"type": "integer", "required": True, "description": "数量", "default": 1},
                    "unit": {"type": "string", "required": True, "description": "单位", "default": "块"}
                },
                "calculation_rules": {
                    "volume": "area * thickness / 1000",
                    "area": "area"
                }
            }
        }
        
        if component_type and component_type in templates:
            return {
                "success": True,
                "data": {component_type: templates[component_type]},
                "message": f"成功获取 {component_type} 模板"
            }
        
        return {
            "success": True,
            "data": templates,
            "message": "成功获取所有构件模板"
        }
        
    except Exception as e:
        logger.error(f"获取构件模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取构件模板失败: {str(e)}")

@router.get("/statistics")
async def get_component_statistics(
    drawing_id: Optional[int] = Query(None, description="图纸ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取构件统计信息"""
    try:
        query = db.query(Drawing).filter(Drawing.user_id == current_user.id)
        
        if drawing_id:
            query = query.filter(Drawing.id == drawing_id)
        
        drawings = query.all()
        
        stats = {
            "total_components": 0,
            "by_type": {},
            "by_material": {},
            "total_volume": 0,
            "total_area": 0,
            "drawings_count": len(drawings)
        }
        
        for drawing in drawings:
            if drawing.processing_result:
                try:
                    import json
                    if isinstance(drawing.processing_result, str):
                        result = json.loads(drawing.processing_result)
                    else:
                        result = drawing.processing_result
                    
                    components = result.get('final_components', [])
                    stats["total_components"] += len(components)
                    
                    for comp in components:
                        # 按类型统计
                        comp_type = comp.get('type', 'unknown')
                        stats["by_type"][comp_type] = stats["by_type"].get(comp_type, 0) + 1
                        
                        # 按材料统计
                        material = comp.get('material', 'unknown')
                        stats["by_material"][material] = stats["by_material"].get(material, 0) + 1
                        
                        # 体积和面积累计
                        if comp.get('volume'):
                            stats["total_volume"] += float(comp.get('volume', 0))
                        if comp.get('area'):
                            stats["total_area"] += float(comp.get('area', 0))
                            
                except (json.JSONDecodeError, AttributeError, ValueError) as e:
                    logger.warning(f"解析图纸 {drawing.id} 统计数据失败: {e}")
                    continue
        
        return {
            "success": True,
            "data": stats,
            "message": "成功获取构件统计信息"
        }
        
    except Exception as e:
        logger.error(f"获取构件统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取构件统计信息失败: {str(e)}") 