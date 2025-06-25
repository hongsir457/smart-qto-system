import os
import json
import logging
import time
import math
import base64
import tempfile
from typing import Dict, Any, List, Optional, Tuple

from ..enhanced_slice_models import EnhancedSliceInfo, OCRTextItem

logger = logging.getLogger(__name__)

class SliceManager:
    """
    切片管理器
    负责共享切片的复用、加载和唯一性ID修复等功能。
    """

    def __init__(self):
        pass

    def can_reuse_shared_slices(self, shared_slice_results: Dict[str, Any], image_path: str) -> bool:
        """检查是否可以复用共享切片结果"""
        if not shared_slice_results:
            return False
        
        image_name = os.path.basename(image_path)
        slice_info = shared_slice_results.get(image_path)
        if not slice_info:
            for path, info in shared_slice_results.items():
                if os.path.basename(path) == image_name:
                    slice_info = info
                    break
        
        if not slice_info or not slice_info.get('sliced', False) or not slice_info.get('slice_infos', []):
            return False
        
        logger.info(f"✅ 发现可复用的智能切片: {len(slice_info.get('slice_infos', []))} 个切片")
        return True

    def reuse_shared_slices(self, shared_slice_results: Dict[str, Any], image_path: str, drawing_info: Dict[str, Any]) -> Dict[str, Any]:
        """复用共享切片结果"""
        try:
            image_name = os.path.basename(image_path)
            slice_data_map = shared_slice_results.get(image_path)
            if not slice_data_map:
                for path, info in shared_slice_results.items():
                    if os.path.basename(path) == image_name:
                        slice_data_map = info
                        break
            
            if not slice_data_map:
                return {"success": False, "error": "未找到对应的切片信息"}
            
            slice_infos_raw = slice_data_map.get('slice_infos', [])
            original_width = slice_data_map.get('original_width', 0)
            original_height = slice_data_map.get('original_height', 0)
            
            logger.info(f"♻️ 复用智能切片: {len(slice_infos_raw)} 个切片，原图尺寸: {original_width}x{original_height}")
            
            enhanced_slices = []
            for i, slice_data in enumerate(slice_infos_raw):
                try:
                    slice_image_data = base64.b64decode(slice_data.base64_data)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_slice_file:
                        temp_slice_file.write(slice_image_data)
                        slice_path = temp_slice_file.name

                    row, col = self._calculate_slice_coords(i, len(slice_infos_raw), original_width, original_height, slice_data.x, slice_data.y)
                    
                    enhanced_slice = EnhancedSliceInfo(
                        filename=f"reused_slice_{row}_{col}.png",
                        row=row, col=col,
                        x_offset=slice_data.x, y_offset=slice_data.y,
                        source_page=drawing_info.get("page_number", 1),
                        width=slice_data.width, height=slice_data.height,
                        slice_path=slice_path,
                        ocr_results=[], enhanced_prompt=""
                    )
                    enhanced_slices.append(enhanced_slice)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 复用切片 {i} 失败: {e}")
                    continue
            
            enhanced_slices = self._fix_duplicate_slice_ids(enhanced_slices)

            slice_coordinate_map = {
                f"{s.row}_{s.col}": {
                    'x_offset': s.x_offset, 'y_offset': s.y_offset,
                    'width': s.width, 'height': s.height,
                    'slice_id': f"{s.row}_{s.col}", 'row': s.row, 'col': s.col
                } for s in enhanced_slices
            }

            original_image_info = {
                'width': original_width, 'height': original_height,
                'total_slices': len(enhanced_slices), 'slice_source': 'intelligent_slicer'
            }
            
            return {
                "success": True,
                "enhanced_slices": enhanced_slices,
                "slice_coordinate_map": slice_coordinate_map,
                "original_image_info": original_image_info,
            }
            
        except Exception as e:
            logger.error(f"❌ 智能切片复用失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def load_shared_ocr_results(self, enhanced_slices: List[EnhancedSliceInfo], shared_slice_results: Dict[str, Any], image_path: str) -> Dict[str, Any]:
        """从共享切片结果中加载OCR数据"""
        image_name = os.path.basename(image_path)
        slice_info_map = shared_slice_results.get(image_path)
        if not slice_info_map:
            for path, info in shared_slice_results.items():
                if os.path.basename(path) == image_name:
                    slice_info_map = info
                    break

        if not slice_info_map or not slice_info_map.get('sliced'):
            return {"success": False, "error": "在共享结果中未找到有效的切片信息"}

        total_loaded_texts = 0
        total_slices_with_ocr = 0

        # Create a quick lookup for original slices
        original_slices_lookup = {s.slice_id: s for s in slice_info_map.get('slice_infos', [])}

        for es in enhanced_slices:
            original_slice = original_slices_lookup.get(es.filename)
            if original_slice and hasattr(original_slice, 'ocr_results') and original_slice.ocr_results:
                ocr_items = self._convert_to_ocr_text_items(original_slice.ocr_results)
                es.ocr_results = ocr_items
                total_loaded_texts += len(ocr_items)
                total_slices_with_ocr += 1

        logger.info(f"✅ 从共享结果加载OCR数据: {total_slices_with_ocr}/{len(enhanced_slices)} 个切片，{total_loaded_texts} 个文本项")
        return {"success": True, "loaded_text_count": total_loaded_texts, "enhanced_slices": enhanced_slices}

    def _calculate_slice_coords(self, index: int, total_slices: int, img_w: int, img_h: int, x: int, y: int) -> Tuple[int, int]:
        """根据切片在图片中的位置智能计算行列，避免重复标识"""
        if img_w > 0 and img_h > 0:
            estimated_rows = math.ceil(math.sqrt(total_slices * img_h / img_w))
            estimated_cols = math.ceil(total_slices / estimated_rows)
            row_height = max(1, img_h // estimated_rows)
            col_width = max(1, img_w // estimated_cols)
            row = min(y // row_height, estimated_rows - 1)
            col = min(x // col_width, estimated_cols - 1)
        else:
            estimated_cols = max(1, math.ceil(math.sqrt(total_slices)))
            row = index // estimated_cols
            col = index % estimated_cols
        return max(0, row), max(0, col)

    def _fix_duplicate_slice_ids(self, enhanced_slices: List[EnhancedSliceInfo]) -> List[EnhancedSliceInfo]:
        """修复重复的切片标识"""
        used_coordinates = set()
        fixed_count = 0
        
        for i, slice_info in enumerate(enhanced_slices):
            original_coord = (slice_info.row, slice_info.col)
            
            if original_coord in used_coordinates:
                estimated_cols = max(1, math.ceil(math.sqrt(len(enhanced_slices))))
                new_row, new_col = i // estimated_cols, i % estimated_cols
                
                retry_count = 0
                while (new_row, new_col) in used_coordinates and retry_count < 100:
                    new_row = (i + retry_count) // estimated_cols
                    new_col = (i + retry_count) % estimated_cols
                    retry_count += 1
                
                slice_info.row, slice_info.col = new_row, new_col
                slice_info.filename = f"reused_slice_{new_row}_{new_col}.png"
                fixed_count += 1
            
            used_coordinates.add((slice_info.row, slice_info.col))
        
        if fixed_count > 0:
            logger.info(f"✅ 切片标识修复完成: 修复了 {fixed_count} 个重复标识")
        return enhanced_slices

    def _convert_to_ocr_text_items(self, ocr_data: List[Dict]) -> List[OCRTextItem]:
        """将字典格式的OCR数据转换为OCRTextItem对象"""
        ocr_items = []
        for item in ocr_data:
            try:
                if isinstance(item, dict):
                    ocr_items.append(OCRTextItem(
                        text=item.get('text', ''),
                        position=item.get('position', []),
                        confidence=item.get('confidence', 0.0),
                        category=item.get('category', 'unknown'),
                        bbox=item.get('bbox', {})
                    ))
                elif hasattr(item, 'text'):
                    ocr_items.append(item)
            except Exception as e:
                logger.debug(f"⚠️ 转换OCR项失败: {e}")
                continue
        return ocr_items 