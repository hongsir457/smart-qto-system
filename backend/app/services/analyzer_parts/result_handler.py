import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


class ResultHandler:
    """处理Vision结果解析与双轨结果融合的逻辑"""

    def parse_vision_components(self, slice_info, vision_data: Dict[str, Any]) -> List:
        """从Vision API的响应中解析构件列表 - 增强版"""
        from app.schemas.component import DrawingComponent, ComponentPosition, ComponentConfidence

        components_from_vision = []
        raw_components = vision_data.get("components", [])

        if not raw_components:
            logger.warning(f"切片 {slice_info.filename} 的Vision分析未返回任何构件")
            return []

        for i, comp_data in enumerate(raw_components):
            try:
                component_id_str = comp_data.get("component_id", f"unknown_{slice_info.filename}_{i}")
                component_type_str = comp_data.get("component_type", "未知")
                
                bbox_local = None
                
                if "bbox" in comp_data:
                    bbox_raw = comp_data["bbox"]
                    if isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                        bbox_local = bbox_raw
                    elif isinstance(bbox_raw, dict) and all(k in bbox_raw for k in ["x", "y", "width", "height"]):
                        bbox_local = [bbox_raw["x"], bbox_raw["y"], bbox_raw["width"], bbox_raw["height"]]
                
                if not bbox_local and "location" in comp_data:
                    location = comp_data["location"]
                    if isinstance(location, dict) and "bbox" in location:
                        bbox_raw = location["bbox"]
                        if isinstance(bbox_raw, dict) and all(k in bbox_raw for k in ["x", "y", "width", "height"]):
                            bbox_local = [bbox_raw["x"], bbox_raw["y"], bbox_raw["width"], bbox_raw["height"]]
                        elif isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                            bbox_local = bbox_raw
                
                if not bbox_local and "geometry" in comp_data:
                    geometry = comp_data["geometry"]
                    if isinstance(geometry, dict) and "bbox" in geometry:
                        bbox_raw = geometry["bbox"]
                        if isinstance(bbox_raw, dict) and all(k in bbox_raw for k in ["x", "y", "width", "height"]):
                            bbox_local = [bbox_raw["x"], bbox_raw["y"], bbox_raw["width"], bbox_raw["height"]]
                        elif isinstance(bbox_raw, list) and len(bbox_raw) == 4:
                            bbox_local = bbox_raw
                
                if not bbox_local or not isinstance(bbox_local, list) or len(bbox_local) != 4:
                    logger.warning(f"构件 {component_id_str} 缺少有效的bbox，尝试生成默认值")
                    bbox_local = [0, 0, 100, 50]
                
                preliminary_component = {
                    "id": f"{slice_info.filename}_{component_id_str}",
                    "component_type": component_type_str,
                    "component_id": component_id_str,
                    "position": {
                        "slice_id": slice_info.filename,
                        "bbox_local": tuple(bbox_local),
                        "bbox_global": (0, 0, 0, 0)
                    },
                    "source_modules": ["Vision"],
                    "confidence": {
                        "vision_confidence": comp_data.get("confidence", 0.8),
                        "fusion_confidence": comp_data.get("confidence", 0.8)
                    },
                    "floor": vision_data.get("drawing_info", {}).get("floor_level"),
                    "drawing_name": vision_data.get("drawing_info", {}).get("title"),
                    "raw_vision_data": comp_data
                }

                components_from_vision.append(preliminary_component)
                logger.debug(f"✅ 成功解析构件 {component_id_str}，bbox: {bbox_local}")

            except Exception as e:
                error_message = str(e).replace('\\', '/')
                logger.error(f"解析Vision构件时出错: {error_message} - 数据: {comp_data}")
                continue
                
        logger.info(f"切片 {slice_info.filename} 解析出 {len(components_from_vision)} 个构件")
        return components_from_vision

    def merge_dual_track_results(self, analyzer) -> Dict[str, Any]:
        """融合双轨结果（OCR + Vision）"""
        from app.services.result_mergers.vision_ocr_fusion import VisionOCRFusionService

        logger.info("🚀 开始使用VisionOCRFusionService进行高级融合...")

        all_vision_components = []
        for slice_filename, components in analyzer.slice_components.items():
            all_vision_components.extend(components)

        all_ocr_items = []
        for slice_info in analyzer.enhanced_slices:
            if slice_info.ocr_results:
                all_ocr_items.extend(asdict(item) for item in slice_info.ocr_results)

        try:
            if not analyzer.coordinate_service or not hasattr(analyzer.coordinate_service, 'slice_coordinate_map') or not analyzer.coordinate_service.slice_coordinate_map:
                logger.warning("⚠️ 坐标转换服务未初始化或无slice_coordinate_map，尝试自动重建...")
                slice_coordinate_map = {}
                for slice_info in analyzer.enhanced_slices:
                    slice_key = f"{slice_info.row}_{slice_info.col}"
                    slice_coordinate_map[slice_key] = {
                        'x_offset': slice_info.x_offset,
                        'y_offset': slice_info.y_offset,
                        'width': slice_info.width,
                        'height': slice_info.height
                    }
                if analyzer.coordinate_service:
                    analyzer.coordinate_service.slice_coordinate_map = slice_coordinate_map
                else:
                    logger.error("❌ 无法重建坐标服务，coordinate_service为None")
                    return {"success": False, "error": "Coordinate service not initialized and cannot be rebuilt"}
                logger.info(f"✅ 自动重建slice_coordinate_map: {len(slice_coordinate_map)} 个切片")
        except Exception as e:
            logger.error(f"❌ 自动重建slice_coordinate_map失败: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to rebuild slice_coordinate_map: {e}"}

        fusion_service = VisionOCRFusionService(analyzer.coordinate_service.slice_coordinate_map)
        try:
            fused_components = fusion_service.fuse_results(all_vision_components, all_ocr_items)
            analyzer.merged_components = fused_components
            logger.info(f"✅ 成功融合了 {len(fused_components)} 个构件")
            if len(fused_components) == 0:
                logger.warning(f"⚠️ 融合后构件为0，all_vision_components数量: {len(all_vision_components)}，all_ocr_items数量: {len(all_ocr_items)}")
                logger.warning(f"示例Vision构件: {all_vision_components[:2]}")
                logger.warning(f"示例OCR项: {all_ocr_items[:2]}")
            return {"success": True, "merged_count": len(fused_components)}
        except Exception as e:
            error_message = str(e).replace('\\', '/')
            logger.error(f"❌ 调用VisionOCRFusionService时发生错误: {error_message}", exc_info=True)
            return {"success": False, "error": f"Fusion service failed: {str(e)}"} 