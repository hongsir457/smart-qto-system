from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class DrawingBase(BaseModel):
    filename: str
    file_type: Optional[str] = None
    status: str = "uploaded"
    error_message: Optional[str] = None

class DrawingCreate(DrawingBase):
    user_id: Optional[int] = None
    file_size: Optional[int] = None

class DrawingUpdate(BaseModel):
    status: Optional[str] = None
    recognition_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_result: Optional[Dict[str, Any]] = None
    components_count: Optional[int] = None
    s3_urls: Optional[Dict[str, Any]] = None

class Drawing(DrawingBase):
    id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[int] = None
    recognition_results: Optional[Dict[str, Any]] = None
    ocr_results: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    processing_result: Optional[Dict[str, Any]] = None
    components_count: Optional[int] = None
    s3_urls: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class DrawingResponse(BaseModel):
    """API响应模型"""
    id: int
    filename: str
    status: str
    user_id: int
    created_at: Optional[datetime] = None
    message: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    error_message: Optional[str] = None
    recognition_results: Optional[Dict[str, Any]] = None
    ocr_results: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None
    task_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DrawingStatus(BaseModel):
    """图纸处理状态响应"""
    id: int
    filename: str
    status: str
    progress: int  # 处理进度百分比
    components_count: int
    processing_time: float
    stages_completed: List[str]
    s3_urls: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DrawingInDB(Drawing):
    """用于数据库操作的图纸模型"""
    pass

class DrawingList(BaseModel):
    """分页响应模型"""
    items: List[DrawingResponse]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)

class OCRTextRegion(BaseModel):
    """OCR识别的文本区域"""
    text: str
    confidence: float
    bbox: Dict[str, float]
    bbox_area: float
    text_length: int
    is_number: bool
    is_dimension: bool
    is_component_code: bool

class OCRStatistics(BaseModel):
    """OCR统计信息"""
    total_count: int
    numeric_count: int
    dimension_count: int
    component_code_count: int
    avg_confidence: float

class TitleBlockInfo(BaseModel):
    """图框信息"""
    project_name: Optional[str] = None
    drawing_title: Optional[str] = None
    drawing_number: Optional[str] = None
    drawing_type: Optional[str] = None
    scale: Optional[str] = None
    designer: Optional[str] = None
    checker: Optional[str] = None
    date: Optional[str] = None

class ComponentInfo(BaseModel):
    """构件信息"""
    code: str
    component_type: str
    dimensions: List[str]
    position: Dict[str, float]
    confidence: float

class StageOneAnalysisResponse(BaseModel):
    """一阶段分析响应"""
    drawing_type: str
    title_block: TitleBlockInfo
    components: List[ComponentInfo]
    dimensions: List[Dict[str, Any]]
    component_list: List[Dict[str, Any]]
    statistics: Dict[str, Any]

class OCRResultsResponse(BaseModel):
    """OCR结果响应"""
    drawing_id: int
    status: str
    ocr_data: Dict[str, Any]
    stage_one_analysis: StageOneAnalysisResponse
    quality_info: Dict[str, Any]
    message: Optional[str] = None

class LLMAnalysisInfo(BaseModel):
    """大模型分析信息"""
    model_used: str
    analysis_rounds: int
    overall_confidence: float
    conversation_history: List[Dict[str, Any]]

class AnalysisResultsResponse(BaseModel):
    """二阶段分析结果响应"""
    drawing_id: int
    analysis_type: str  # "stage_two" 或 "stage_one_fallback"
    has_ai_analysis: bool
    components: List[Dict[str, Any]]
    analysis_summary: Dict[str, Any]
    quality_assessment: Dict[str, Any]
    recommendations: List[str]
    statistics: Dict[str, Any]
    llm_analysis: Optional[LLMAnalysisInfo] = None

class ComponentsResponse(BaseModel):
    """构件清单响应"""
    drawing_id: int
    components: List[Dict[str, Any]]
    total_count: int
    analysis_info: Dict[str, Any]
    quality_metrics: Dict[str, Any] 