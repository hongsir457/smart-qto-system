# OCR增强与分类相关方法
from .enhanced_slice_models import OCRTextItem, EnhancedSliceInfo
import logging
import re
from typing import List
logger = logging.getLogger(__name__)

class OCREnhancer:
    def __init__(self, component_patterns):
        self.component_patterns = component_patterns

    def classify_ocr_texts(self, ocr_results: List[OCRTextItem]):
        for ocr_item in ocr_results:
            text = ocr_item.text.strip()
            for category, patterns in self.component_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, text, re.IGNORECASE):
                        ocr_item.category = category
                        break
                if ocr_item.category != "unknown":
                    break

    def enhance_slices_with_ocr(self, enhanced_slices: List[EnhancedSliceInfo]):
        enhanced_count = 0
        for slice_info in enhanced_slices:
            if not slice_info.ocr_results:
                continue
            self.classify_ocr_texts(slice_info.ocr_results)
            enhanced_count += 1
        logger.info(f"📊 OCR增强完成: {enhanced_count}/{len(enhanced_slices)} 个切片")
        return {"success": True, "enhanced_slices": enhanced_count, "total_slices": len(enhanced_slices)} 