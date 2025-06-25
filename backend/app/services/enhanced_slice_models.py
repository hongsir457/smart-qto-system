from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class OCRTextItem:
    """OCR文本项"""
    text: str
    position: List[List[int]]  # 四个角点坐标
    confidence: float
    category: str = "unknown"  # 分类：component_id, dimension, material, axis, etc.
    bbox: Optional[Dict[str, int]] = None  # 标准化边界框

@dataclass
class EnhancedSliceInfo:
    """增强切片信息（包含OCR结果）"""
    filename: str
    row: int
    col: int
    x_offset: int
    y_offset: int
    source_page: int
    width: int
    height: int
    slice_path: str
    ocr_results: List[OCRTextItem] = None
    enhanced_prompt: str = "" 