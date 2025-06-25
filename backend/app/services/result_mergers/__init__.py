"""
结果合并器模块
用于合并切片处理的结果
"""

from .ocr_slice_merger import OCRSliceMerger, OCRFullResult
from .vision_result_merger import VisionResultMerger, VisionFullResult

__all__ = [
    'OCRSliceMerger',
    'OCRFullResult', 
    'VisionResultMerger',
    'VisionFullResult'
] 