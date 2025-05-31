from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class DrawingBase(BaseModel):
    filename: str
    file_type: str
    status: str
    error_message: Optional[str] = None

class DrawingCreate(DrawingBase):
    pass

class DrawingUpdate(BaseModel):
    status: Optional[str] = None
    recognition_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class Drawing(DrawingBase):
    id: int
    file_path: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int
    recognition_results: Optional[Dict[str, Any]] = None
    ocr_results: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DrawingInDB(Drawing):
    """用于数据库操作的图纸模型"""
    pass

class DrawingList(BaseModel):
    """分页响应模型"""
    items: List[Drawing]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True) 