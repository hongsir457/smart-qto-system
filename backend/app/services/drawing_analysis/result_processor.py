import logging
import time
from typing import Dict, Any, List, Optional

from ..result_mergers.vision_ocr_fusion import VisionOCRFusionService
from ...utils.analysis_optimizations import CoordinateTransformService, AnalysisLogger
from ..enhanced_slice_models import EnhancedSliceInfo

logger = logging.getLogger(__name__)

class ResultProcessor:
    """
    分析结果处理器
    负责融合双轨结果，并进行全局坐标还原。
    """

    def __init__(self, coordinate_service: CoordinateTransformService):
        """
        初始化结果处理器
        
        Args:
            coordinate_service: 坐标转换服务实例
        """
        self.coordinate_service = coordinate_service
        # VisionOCRFusionService is instantiated on-the-fly as it's lightweight
        # and depends on slice_coordinate_map which can be dynamic.

    def process_and_fuse(self, 
                         slice_components: Dict[str, List[Dict]], 
                         enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        """
        融合双轨结果并还原坐标
        
        Args:
            slice_components: 从Vision轨道分析出的每个切片的构件
            enhanced_slices: 增强切片列表（用于获取OCR项和坐标重建）
            
        Returns:
            处理后的结果，包含融合后的构件列表
        """
        try:
            # 1. 融合结果
            fusion_result = self._merge_results(slice_components, enhanced_slices)
            if not fusion_result["success"]:
                return fusion_result # Propagate error
            
            merged_components = fusion_result["merged_components"]
            
            # 2. 坐标还原
            restoration_result = self._restore_coordinates(merged_components)
            if not restoration_result["success"]:
                # Log error but don't fail the whole process
                logger.error(f"⚠️ 坐标还原失败: {restoration_result.get('error')}")
            
            final_components = restoration_result.get("restored_components", merged_components)

            return {"success": True, "final_components": final_components}

        except Exception as e:
            logger.error(f"❌ 结果处理和融合失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _merge_results(self, 
                       slice_components: Dict[str, List[Dict]], 
                       enhanced_slices: List[EnhancedSliceInfo]) -> Dict[str, Any]:
        """融合双轨结果（OCR + Vision）"""
        logger.info("🚀 开始使用VisionOCRFusionService进行高级融合...")

        all_vision_components = [comp for comps in slice_components.values() for comp in comps]
        
        all_ocr_items = []
        for slice_info in enhanced_slices:
            if slice_info.ocr_results:
                # Here we assume OCR items don't have global coords yet and fusion service handles it.
                # If they needed global coords, they would have to be transformed first.
                all_ocr_items.extend(item.to_dict() for item in slice_info.ocr_results)
        
        # Ensure coordinate service has the map
        if not self.coordinate_service or not self.coordinate_service.slice_coordinate_map:
             return {"success": False, "error": "Coordinate service map not initialized."}
        
        fusion_service = VisionOCRFusionService(self.coordinate_service.slice_coordinate_map)
        try:
            fused_components = fusion_service.fuse_results(all_vision_components, all_ocr_items)
            logger.info(f"✅ 成功融合了 {len(fused_components)} 个构件")
            return {"success": True, "merged_components": fused_components}
        except Exception as e:
            logger.error(f"❌ 调用VisionOCRFusionService时发生错误: {e}", exc_info=True)
            return {"success": False, "error": f"Fusion service failed: {str(e)}"}

    def _restore_coordinates(self, components: List[Any]) -> Dict[str, Any]:
        """执行全局坐标还原"""
        if not components:
            return {"success": True, "restored_components": []}

        start_time = time.time()
        restored_count = 0
        
        # This uses the CoordinateRestorer logic, which is now part of this service
        for component in components:
            try:
                # The fusion service should have already populated component.position
                pos = component.get("position", {})
                bbox_local = pos.get("bbox_local")
                slice_id = pos.get("slice_id")

                if bbox_local and slice_id:
                    global_bbox = self.coordinate_service.transform_bbox_to_global(bbox_local, slice_id)
                    component["position"]["bbox_global"] = global_bbox
                    restored_count += 1
            except Exception as e:
                comp_id = component.get('id', 'unknown')
                logger.warning(f"⚠️ 构件 {comp_id} 的坐标转换失败: {e}")
                continue
        
        logger.info(f"✅ 坐标还原完成: {restored_count}/{len(components)}个构件")
        return {"success": True, "restored_components": components} 