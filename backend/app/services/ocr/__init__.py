# -*- coding: utf-8 -*-
"""
OCR服务模块 - 集成智能切片功能
"""

from .paddle_ocr import PaddleOCRService as OriginalPaddleOCRService
from .paddle_ocr_service import PaddleOCRService
from .paddle_ocr_with_slicing import PaddleOCRWithSlicing

__all__ = [
    'PaddleOCRService',           # 增强版服务（推荐使用）
    'OriginalPaddleOCRService',   # 原始服务
    'PaddleOCRWithSlicing'        # 纯切片服务
] 