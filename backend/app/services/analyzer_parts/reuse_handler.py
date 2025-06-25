import logging
from typing import Dict, Any, List, Optional
import os
import math
import base64
import tempfile

from ..enhanced_slice_models import OCRTextItem, EnhancedSliceInfo

logger = logging.getLogger(__name__)


class ReuseHandler:
    """处理与缓存复用相关的逻辑"""

    def can_reuse_slice_ocr(self, analyzer, slice_info: EnhancedSliceInfo) -> bool:
        """检查是否可以复用切片的OCR结果"""
        try:
            # 检查共享切片结果中是否有OCR数据
            if hasattr(analyzer, 'shared_slice_results') and analyzer.shared_slice_results:
                for original_path, slice_result in analyzer.shared_slice_results.items():
                    slice_infos = slice_result.get('slice_infos', [])
                    for info in slice_infos:
                        if (info.get('row') == slice_info.row and
                            info.get('col') == slice_info.col and
                            info.get('ocr_results')):
                            return True
            
            # 检查内存缓存
            if hasattr(analyzer, '_slice_ocr_cache'):
                slice_key = f"{slice_info.row}_{slice_info.col}_{slice_info.slice_path}"
                return slice_key in analyzer._slice_ocr_cache
            
            return False
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.debug(f"⚠️ 检查OCR复用失败: {error_message}")
            return False

    def load_cached_ocr_results(self, analyzer, slice_info: EnhancedSliceInfo) -> List[OCRTextItem]:
        """加载缓存的OCR结果"""
        try:
            # 优先从共享切片结果加载
            if hasattr(analyzer, 'shared_slice_results') and analyzer.shared_slice_results:
                for original_path, slice_result in analyzer.shared_slice_results.items():
                    slice_infos = slice_result.get('slice_infos', [])
                    for info in slice_infos:
                        if (info.get('row') == slice_info.row and
                            info.get('col') == slice_info.col):
                            ocr_data = info.get('ocr_results', [])
                            if ocr_data:
                                # 转换为OCRTextItem对象
                                return self.convert_to_ocr_text_items(ocr_data)
            
            # 从内存缓存加载
            if hasattr(analyzer, '_slice_ocr_cache'):
                slice_key = f"{slice_info.row}_{slice_info.col}_{slice_info.slice_path}"
                cached_data = analyzer._slice_ocr_cache.get(slice_key)
                if cached_data:
                    return self.convert_to_ocr_text_items(cached_data)
            
            return []
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.debug(f"⚠️ 加载缓存OCR结果失败: {error_message}")
            return []

    def convert_to_ocr_text_items(self, ocr_data: List[Dict]) -> List[OCRTextItem]:
        """将字典格式的OCR数据转换为OCRTextItem对象"""
        ocr_items = []
        
        for item in ocr_data:
            try:
                if isinstance(item, dict):
                    ocr_item = OCRTextItem(
                        text=item.get('text', ''),
                        position=item.get('position', []),
                        confidence=item.get('confidence', 0.0),
                        category=item.get('category', 'unknown'),
                        bbox=item.get('bbox', {})
                    )
                    ocr_items.append(ocr_item)
                elif hasattr(item, 'text'):  # 已经是OCRTextItem对象
                    ocr_items.append(item)
                    
            except Exception as e:
                error_message = str(e).replace('\\', '/')
                logger.debug(f"⚠️ 转换OCR项失败: {error_message}")
                continue
        
        return ocr_items

    def cache_slice_ocr_results(self, analyzer, slice_info: EnhancedSliceInfo):
        """缓存切片的OCR结果"""
        try:
            if not hasattr(analyzer, '_slice_ocr_cache'):
                analyzer._slice_ocr_cache = {}
            
            slice_key = f"{slice_info.row}_{slice_info.col}_{slice_info.slice_path}"
            
            # 转换OCRTextItem为字典格式
            ocr_data = []
            for ocr_item in slice_info.ocr_results or []:
                ocr_data.append({
                    'text': ocr_item.text,
                    'position': ocr_item.position,
                    'confidence': ocr_item.confidence,
                    'category': ocr_item.category,
                    'bbox': ocr_item.bbox
                })
            
            analyzer._slice_ocr_cache[slice_key] = ocr_data
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.debug(f"⚠️ 缓存OCR结果失败: {error_message}")

    def save_global_ocr_cache(self, analyzer):
        """保存全局OCR缓存"""
        try:
            if not hasattr(analyzer, '_global_ocr_cache'):
                analyzer._global_ocr_cache = {}
            
            # 保存所有切片的OCR结果
            for slice_info in analyzer.enhanced_slices:
                if slice_info.ocr_results:
                    slice_key = f"{slice_info.row}_{slice_info.col}"
                    ocr_data = []
                    for ocr_item in slice_info.ocr_results:
                        ocr_data.append({
                            'text': ocr_item.text,
                            'position': ocr_item.position,
                            'confidence': ocr_item.confidence,
                            'category': ocr_item.category,
                            'bbox': ocr_item.bbox
                        })
                    analyzer._global_ocr_cache[slice_key] = ocr_data
            
            logger.debug(f"💾 全局OCR缓存已保存: {len(analyzer._global_ocr_cache)} 个切片")
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.debug(f"⚠️ 保存全局OCR缓存失败: {error_message}")

    def reuse_global_ocr_cache(self, analyzer) -> Dict[str, Any]:
        """复用全局OCR缓存"""
        try:
            total_text_items = 0
            reused_slices = 0
            
            for slice_info in analyzer.enhanced_slices:
                slice_key = f"{slice_info.row}_{slice_info.col}"
                
                if slice_key in analyzer._global_ocr_cache:
                    ocr_data = analyzer._global_ocr_cache[slice_key]
                    slice_info.ocr_results = self.convert_to_ocr_text_items(ocr_data)
                    total_text_items += len(slice_info.ocr_results)
                    reused_slices += 1
                    logger.debug(f"♻️ 切片 {slice_key} 复用全局缓存: {len(slice_info.ocr_results)} 个文本项")
                else:
                    slice_info.ocr_results = []
            
            logger.info(f"♻️ 全局OCR缓存复用完成: {reused_slices}/{len(analyzer.enhanced_slices)} 个切片, 共 {total_text_items} 个文本项")
            
            return {
                "success": True,
                "statistics": {
                    "processed_slices": 0,
                    "reused_slices": reused_slices,
                    "total_slices": len(analyzer.enhanced_slices),
                    "total_text_items": total_text_items,
                    "success_rate": reused_slices / len(analyzer.enhanced_slices) if analyzer.enhanced_slices else 0,
                    "reuse_rate": 1.0
                }
            }
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.error(f"❌ 复用全局OCR缓存失败: {error_message}")
            return {"success": False, "error": str(e)}

    def can_reuse_shared_slices(self, shared_slice_results: Dict[str, Any], image_path: str) -> bool:
        """检查是否可以复用共享切片结果"""
        if not shared_slice_results:
            return False
        
        # 检查是否有对应图像的切片结果
        slice_info = shared_slice_results.get(image_path)
        if not slice_info:
            # 尝试用文件名匹配
            image_name = os.path.basename(image_path)
            for path, info in shared_slice_results.items():
                if os.path.basename(path) == image_name:
                    slice_info = info
                    break
        
        if not slice_info:
            return False
        
        # 检查切片结果是否有效
        if not slice_info.get('sliced', False):
            return False
        
        slice_infos = slice_info.get('slice_infos', [])
        if not slice_infos:
            return False
        
        logger.info(f"✅ 发现可复用的智能切片: {len(slice_infos)} 个切片")
        return True

    def reuse_shared_slices(self, analyzer, shared_slice_results: Dict[str, Any], image_path: str, drawing_info: Dict[str, Any]) -> Dict[str, Any]:
        """复用共享切片结果"""
        try:
            # 获取切片信息
            slice_info_data = shared_slice_results.get(image_path)
            if not slice_info_data:
                # 尝试用文件名匹配
                image_name = os.path.basename(image_path)
                for path, info in shared_slice_results.items():
                    if os.path.basename(path) == image_name:
                        slice_info_data = info
                        break
            
            if not slice_info_data:
                return {"success": False, "error": "未找到对应的切片信息"}
            
            slice_infos = slice_info_data.get('slice_infos', [])
            original_width = slice_info_data.get('original_width', 0)
            original_height = slice_info_data.get('original_height', 0)
            
            logger.info(f"♻️ 复用智能切片: {len(slice_infos)} 个切片，原图尺寸: {original_width}x{original_height}")
            
            # 转换为EnhancedSliceInfo格式
            analyzer.enhanced_slices = []
            ocr_text_count = 0
            used_coordinates = set()  # 防重复坐标集合
            
            for i, slice_data in enumerate(slice_infos):
                try:
                    slice_image_data = base64.b64decode(slice_data.base64_data)
                    temp_slice_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    temp_slice_file.write(slice_image_data)
                    temp_slice_file.close()
                    
                    if original_width > 0 and original_height > 0:
                        total_slices = len(slice_infos)
                        estimated_rows = math.ceil(math.sqrt(total_slices * original_height / original_width))
                        estimated_cols = math.ceil(total_slices / estimated_rows)
                        
                        if estimated_rows > 0 and estimated_cols > 0:
                            row_height = max(1, original_height // estimated_rows)
                            col_width = max(1, original_width // estimated_cols)
                            row = min(slice_data.y // row_height, estimated_rows - 1)
                            col = min(slice_data.x // col_width, estimated_cols - 1)
                        else:
                            estimated_cols = max(1, math.ceil(math.sqrt(len(slice_infos))))
                            row = i // estimated_cols
                            col = i % estimated_cols
                    else:
                        estimated_cols = max(1, math.ceil(math.sqrt(len(slice_infos))))
                        row = i // estimated_cols
                        col = i % estimated_cols
                    
                    row = max(0, row)
                    col = max(0, col)
                    
                    original_coord = (row, col)
                    if original_coord in used_coordinates:
                        estimated_cols = max(1, math.ceil(math.sqrt(len(slice_infos))))
                        row = i // estimated_cols
                        col = i % estimated_cols
                        
                        retry_count = 0
                        while (row, col) in used_coordinates and retry_count < 100:
                            row = i // estimated_cols + retry_count // estimated_cols
                            col = (i + retry_count) % estimated_cols
                            retry_count += 1
                    
                    used_coordinates.add((row, col))
                    
                    enhanced_slice_info = EnhancedSliceInfo(
                        filename=f"reused_slice_{row}_{col}.png",
                        row=row,
                        col=col,
                        x_offset=slice_data.x,
                        y_offset=slice_data.y,
                        source_page=drawing_info.get("page_number", 1),
                        width=slice_data.width,
                        height=slice_data.height,
                        slice_path=temp_slice_file.name,
                        ocr_results=[],
                        enhanced_prompt=""
                    )
                    
                    analyzer.enhanced_slices.append(enhanced_slice_info)
                    
                except Exception as e:
                    error_message = str(e).replace('\\', '/')
                    logger.warning(f"⚠️ 复用切片 {i} 失败: {error_message}")
                    continue
            
            self.fix_duplicate_slice_ids(analyzer)
            
            ocr_reused = False
            if hasattr(slice_info_data, 'ocr_results') or 'ocr_results' in slice_info_data:
                logger.info("♻️ 发现可复用的OCR结果")
                ocr_reused = True
                ocr_text_count = len(slice_info_data.get('ocr_results', []))
            
            if analyzer.enhanced_slices:
                rows = [s.row for s in analyzer.enhanced_slices]
                cols = [s.col for s in analyzer.enhanced_slices]
                logger.info(f"✅ 智能切片复用完成: {len(analyzer.enhanced_slices)} 个切片")
                logger.info(f"📍 切片范围: 行 {min(rows)}-{max(rows)}, 列 {min(cols)}-{max(cols)}")
                logger.info(f"📍 切片标识: {[f'{s.row}_{s.col}' for s in analyzer.enhanced_slices[:5]]}{'...' if len(analyzer.enhanced_slices) > 5 else ''}")
            else:
                logger.info(f"✅ 智能切片复用完成: {len(analyzer.enhanced_slices)} 个切片")
            
            slice_coordinate_map = {}
            for s_info in analyzer.enhanced_slices:
                slice_key = f"{s_info.row}_{s_info.col}"
                slice_coordinate_map[slice_key] = {
                    'x_offset': s_info.x_offset,
                    'y_offset': s_info.y_offset,
                    'width': s_info.width,
                    'height': s_info.height,
                    'slice_id': slice_key,
                    'row': s_info.row,
                    'col': s_info.col
                }
            
            original_image_info = {
                'width': original_width,
                'height': original_height,
                'total_slices': len(analyzer.enhanced_slices),
                'slice_source': 'intelligent_slicer'
            }
            
            logger.info(f"✅ 坐标映射构建完成: {len(slice_coordinate_map)} 个切片映射")
            
            return {
                "success": True,
                "slice_count": len(analyzer.enhanced_slices),
                "grid_size": f"智能切片复用",
                "slice_reused": True,
                "ocr_reused": ocr_reused,
                "original_slice_count": len(slice_infos),
                "slice_source": "intelligent_slicer",
                "ocr_statistics": {
                    "reused_ocr_count": ocr_text_count,
                    "reused_from": "shared_slice_results"
                },
                "slice_coordinate_map": slice_coordinate_map,
                "original_image_info": original_image_info
            }
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.error(f"❌ 智能切片复用失败: {error_message}")
            return {"success": False, "error": str(e)}

    def load_shared_ocr_results(self, analyzer, shared_slice_results: Dict[str, Any], image_path: str) -> Dict[str, Any]:
        """从共享切片结果中加载OCR数据"""
        slice_info_data = shared_slice_results.get(image_path)
        if not slice_info_data or not slice_info_data.get('sliced'):
            return {"success": False, "error": "在共享结果中未找到有效的切片信息"}

        total_loaded_texts = 0
        total_slices_with_ocr = 0

        for slice_data in analyzer.enhanced_slices:
            original_slice = next((s for s in slice_info_data.get('slice_infos', []) if s.slice_id == slice_data.filename), None)
            
            if original_slice and hasattr(original_slice, 'ocr_results') and original_slice.ocr_results:
                ocr_items = self.convert_to_ocr_text_items(original_slice.ocr_results)
                slice_data.ocr_results = ocr_items
                total_loaded_texts += len(ocr_items)
                total_slices_with_ocr += 1

        logger.info(f"✅ 从共享结果加载OCR数据: {total_slices_with_ocr}/{len(analyzer.enhanced_slices)} 个切片，{total_loaded_texts} 个文本项")
        
        return {"success": True, "loaded_text_count": total_loaded_texts}

    def fix_duplicate_slice_ids(self, analyzer):
        """修复重复的切片标识"""
        try:
            slice_ids = [f"{s.row}_{s.col}" for s in analyzer.enhanced_slices]
            if len(slice_ids) == len(set(slice_ids)):
                return
                
            logger.info("🔧 开始修复重复的切片标识...")
            
            used_coordinates = set()
            fixed_count = 0
            
            for i, slice_info in enumerate(analyzer.enhanced_slices):
                original_coord = (slice_info.row, slice_info.col)
                
                if original_coord in used_coordinates:
                    estimated_cols = max(1, math.ceil(math.sqrt(len(analyzer.enhanced_slices))))
                    new_row = i // estimated_cols
                    new_col = i % estimated_cols
                    
                    retry_count = 0
                    while (new_row, new_col) in used_coordinates and retry_count < 100:
                        new_row = (i + retry_count) // estimated_cols
                        new_col = (i + retry_count) % estimated_cols
                        retry_count += 1
                    
                    slice_info.row = new_row
                    slice_info.col = new_col
                    slice_info.filename = f"reused_slice_{new_row}_{new_col}.png"
                    fixed_count += 1
                    
                    logger.debug(f"修复切片 {i}: {original_coord} -> ({new_row}, {new_col})")
                
                used_coordinates.add((slice_info.row, slice_info.col))
            
            logger.info(f"✅ 切片标识修复完成: 修复了 {fixed_count} 个重复标识")
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.error(f"❌ 修复切片标识失败: {error_message}") 