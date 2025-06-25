# -*- coding: utf-8 -*-
"""
融合管理器：负责OCR与Vision双轨结果融合、切片查找等
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)

class FusionManager:
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def merge_dual_track_results(self) -> Dict[str, Any]:
        """
        融合双轨结果（OCR + Vision）- 使用新的融合服务
        """
        from app.services.result_mergers.vision_ocr_fusion import VisionOCRFusionService
        logger.info("🚀 开始使用VisionOCRFusionService进行高级融合...")
        all_vision_components = []
        for slice_filename, components in self.analyzer.slice_components.items():
            all_vision_components.extend(components)
        all_ocr_items = []
        for slice_info in self.analyzer.enhanced_slices:
            if slice_info.ocr_results:
                all_ocr_items.extend(asdict(item) for item in slice_info.ocr_results)
        try:
            if not self.analyzer.coordinate_service or not hasattr(self.analyzer.coordinate_service, 'slice_coordinate_map') or not self.analyzer.coordinate_service.slice_coordinate_map:
                logger.warning("⚠️ 坐标转换服务未初始化或无slice_coordinate_map，尝试自动重建...")
                slice_coordinate_map = {}
                for slice_info in self.analyzer.enhanced_slices:
                    slice_key = f"{slice_info.row}_{slice_info.col}"
                    slice_coordinate_map[slice_key] = {
                        'x_offset': slice_info.x_offset,
                        'y_offset': slice_info.y_offset,
                        'width': slice_info.width,
                        'height': slice_info.height
                    }
                if self.analyzer.coordinate_service:
                    self.analyzer.coordinate_service.slice_coordinate_map = slice_coordinate_map
                else:
                    logger.error("❌ 无法重建坐标服务，coordinate_service为None")
                    return {"success": False, "error": "Coordinate service not initialized and cannot be rebuilt"}
                logger.info(f"✅ 自动重建slice_coordinate_map: {len(slice_coordinate_map)} 个切片")
        except Exception as e:
            logger.error(f"❌ 自动重建slice_coordinate_map失败: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to rebuild slice_coordinate_map: {e}"}
        fusion_service = VisionOCRFusionService(self.analyzer.coordinate_service.slice_coordinate_map)
        try:
            fused_components = fusion_service.fuse_results(all_vision_components, all_ocr_items)
            self.analyzer.merged_components = fused_components
            logger.info(f"✅ 成功融合了 {len(fused_components)} 个构件")
            if len(fused_components) == 0:
                logger.warning(f"⚠️ 融合后构件为0，all_vision_components数量: {len(all_vision_components)}，all_ocr_items数量: {len(all_ocr_items)}")
                logger.warning(f"示例Vision构件: {all_vision_components[:2]}")
                logger.warning(f"示例OCR项: {all_ocr_items[:2]}")
            return {"success": True, "merged_count": len(fused_components)}
        except Exception as e:
            logger.error(f"❌ 调用VisionOCRFusionService时发生错误: {e}", exc_info=True)
            return {"success": False, "error": f"Fusion service failed: {str(e)}"}

    def find_enhanced_slice_info(self, source_block: str) -> Optional[Any]:
        """根据源块ID查找增强切片信息"""
        try:
            first_block = source_block.split(" + ")[0]
            row, col = map(int, first_block.split("_"))
            for slice_info in self.analyzer.enhanced_slices:
                if slice_info.row == row and slice_info.col == col:
                    return slice_info
        except:
            pass
        return None 