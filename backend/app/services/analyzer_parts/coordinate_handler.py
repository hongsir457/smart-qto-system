import logging
from typing import Dict, Any, List, Optional
import time

from app.utils.analysis_optimizations import AnalysisLogger

logger = logging.getLogger(__name__)


class CoordinateHandler:
    """处理与坐标转换和还原相关的逻辑"""

    def initialize_service(self, analyzer, slice_coordinate_map: Dict[str, Any], original_image_info: Dict[str, Any]):
        """初始化坐标转换服务"""
        from app.utils.analysis_optimizations import CoordinateTransformService
        
        if not analyzer.coordinate_service:
            analyzer.coordinate_service = CoordinateTransformService(slice_coordinate_map, original_image_info)
            logger.info("✅ 坐标转换服务首次初始化")
        else:
            # 如果已存在，用新数据更新它
            analyzer.coordinate_service.update_maps(slice_coordinate_map, original_image_info)
            logger.info("✅ 坐标转换服务已使用新数据更新")

    def restore_global_coordinates(self, analyzer, image_path: str) -> Dict[str, Any]:
        """优化的坐标还原，使用统一的坐标转换服务"""
        try:
            if not analyzer.merged_components:
                AnalysisLogger.log_step("coordinate_restore_skip", "没有构件需要坐标还原")
                return {"success": True, "restored_count": 0}
            
            start_time = time.time()
            restored_count = 0
            total_components = len(analyzer.merged_components)
            AnalysisLogger.log_step("coordinate_restoration", f"开始坐标还原: {total_components}个构件")
            
            if not hasattr(analyzer, 'coordinate_service') or not analyzer.coordinate_service:
                logger.warning("⚠️ 坐标转换服务未初始化，无法进行坐标还原")
                return {"success": False, "error": "Coordinate service not initialized"}
            
            # 批量转换坐标
            for component in analyzer.merged_components:
                try:
                    if hasattr(component, 'bbox') and component.bbox:
                        if hasattr(component, 'slice_info'):
                            row = getattr(component.slice_info, 'row', None)
                            col = getattr(component.slice_info, 'col', None)
                            if row is not None and col is not None:
                                slice_id = f"{row}_{col}"
                            else:
                                slice_id = getattr(component, 'source_slice', "0_0")
                        else:
                            slice_id = getattr(component, 'source_slice', "0_0")
                        
                        if isinstance(slice_id, str):
                            safe_slice_id = slice_id.replace('\\', '/')
                        else:
                            safe_slice_id = str(slice_id) # 确保是字符串
                            
                        global_bbox = analyzer.coordinate_service.transform_bbox_to_global(
                            component.bbox, 
                            safe_slice_id
                        )
                        component.global_bbox = global_bbox
                        restored_count += 1
                        
                except Exception as e:
                    comp_id = getattr(component, 'id', 'unknown')
                    error_message = str(e).replace('\\', '/')
                    AnalysisLogger.log_step("coordinate_error", f"坐标转换失败: {comp_id} - {error_message}")
                    continue
            
            processing_time = time.time() - start_time
            summary_str = f"坐标还原完成: {restored_count}/{total_components}个构件，耗时{processing_time:.2f}s"
            AnalysisLogger.log_step("coordinate_restoration_completed", summary_str)
            
            return {
                "success": True,
                "restored_count": restored_count,
                "total_components": total_components,
                "processing_time": processing_time
            }
            
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.error(f"❌ 坐标还原主流程失败: {error_message}")
            return {"success": False, "error": str(e)} 