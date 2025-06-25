import logging
from typing import Dict, List, Any, Optional, Tuple
import math

from app.schemas.component import DrawingComponent, ComponentPosition, ComponentConfidence, ComponentGeometry

logger = logging.getLogger(__name__)

class VisionOCRFusionService:
    """
    一个专门用于融合Vision和OCR分析结果的服务。
    它负责将独立的分析结果（构件、文本）融合成一个丰富、准确的工程量清单。
    """

    def __init__(self, slice_coordinate_map: Dict[str, Any]):
        """
        初始化融合服务。
        
        Args:
            slice_coordinate_map (Dict[str, Any]): 包含切片偏移量等信息的映射表。
                                                   格式: { "slice_id": {"offset_x": 100, "offset_y": 200, ...} }
        """
        self.slice_coordinate_map = slice_coordinate_map

    def fuse_results(self, vision_components: List[Dict], ocr_text_items: List[Dict]) -> List[DrawingComponent]:
        """
        执行Vision和OCR结果的融合。
        
        Args:
            vision_components (List[Dict]): 从Vision分析中提取的初步构件列表（包含bbox_local）。
            ocr_text_items (List[Dict]): 从OCR中提取的所有文本项列表（包含全局坐标）。
            
        Returns:
            List[DrawingComponent]: 一个包含完全填充和丰富的DrawingComponent对象的列表。
        """
        if not vision_components:
            return []

        logger.info(f"🚀 开始融合 {len(vision_components)} 个构件和 {len(ocr_text_items)} 个文本项...")

        # 步骤 1: 恢复每个构件的全局坐标
        restored_components = self._restore_global_coordinates(vision_components)

        # 步骤 2: 将OCR文本关联到构件
        final_components = self._associate_text_to_components(restored_components, ocr_text_items)
        
        logger.info(f"✅ 融合完成，生成 {len(final_components)} 个最终构件。")

        return final_components

    def _restore_global_coordinates(self, components: List[Dict]) -> List[Dict]:
        """
        计算并填充每个构件的全局边界框（bbox_global）。
        """
        for comp in components:
            # 🔧 兼容性修复：处理字典和Pydantic模型两种格式
            if hasattr(comp, 'position'):
                # Pydantic模型格式
                pos = comp.position
                slice_id = getattr(pos, 'slice_id', None)
                bbox_local = getattr(pos, 'bbox_local', None)
            else:
                # 字典格式
                pos = comp.get("position", {})
                slice_id = pos.get("slice_id") if isinstance(pos, dict) else getattr(pos, 'slice_id', None)
                bbox_local = pos.get("bbox_local") if isinstance(pos, dict) else getattr(pos, 'bbox_local', None)
            
            slice_info = self.slice_coordinate_map.get(slice_id)
            
            if slice_id and bbox_local and slice_info:
                offset_x = slice_info.get('x_offset', 0)
                offset_y = slice_info.get('y_offset', 0)
                
                # 计算全局坐标
                x1_global = bbox_local[0] + offset_x
                y1_global = bbox_local[1] + offset_y
                x2_global = bbox_local[2] + offset_x
                y2_global = bbox_local[3] + offset_y
                
                # 🔧 兼容性修复：设置全局坐标
                if hasattr(comp, 'position'):
                    # Pydantic模型格式
                    comp.position.bbox_global = (x1_global, y1_global, x2_global, y2_global)
                else:
                    # 字典格式
                    if isinstance(pos, dict):
                        pos["bbox_global"] = (x1_global, y1_global, x2_global, y2_global)
                    else:
                        pos.bbox_global = (x1_global, y1_global, x2_global, y2_global)
            else:
                # 如果缺少信息，则使用一个无效的占位符
                if hasattr(comp, 'position'):
                    comp.position.bbox_global = (0, 0, 0, 0)
                else:
                    if isinstance(pos, dict):
                        pos["bbox_global"] = (0, 0, 0, 0)
                    else:
                        pos.bbox_global = (0, 0, 0, 0)
        
        return components

    def _associate_text_to_components(self, components: List[Dict], ocr_items: List[Dict]) -> List[DrawingComponent]:
        """
        将OCR文本项关联到最近的构件。
        使用空间搜索优化查找过程。
        """
        final_component_models = []
        
        if not ocr_items:
            # 如果没有OCR信息，直接转换现有构件
            for comp_data in components:
                try:
                    # 类型转换
                    if isinstance(comp_data.get("position"), dict):
                        comp_data["position"] = ComponentPosition(**comp_data["position"])
                    if "geometry" in comp_data and isinstance(comp_data["geometry"], dict):
                        comp_data["geometry"] = ComponentGeometry(**comp_data["geometry"])
                    if isinstance(comp_data.get("confidence"), dict):
                        comp_data["confidence"] = ComponentConfidence(**comp_data["confidence"])
                    final_component_models.append(DrawingComponent(**comp_data))
                except Exception as e:
                    logger.error(f"无法将构件数据转换为DrawingComponent模型 (无OCR): {e} - 数据: {comp_data}")
            return final_component_models

        # 步骤1: 为OCR项构建一个简单的空间网格以便快速查找
        grid_size = 200  # 网格单元大小，可以根据图纸密度调整
        ocr_grid = {}
        for item in ocr_items:
            bbox = item.get("bbox")
            if not bbox: continue
            
            # 使用文本框中心点进行网格划分
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            grid_x, grid_y = int(center_x // grid_size), int(center_y // grid_size)
            
            if (grid_x, grid_y) not in ocr_grid:
                ocr_grid[(grid_x, grid_y)] = []
            ocr_grid[(grid_x, grid_y)].append(item)

        # 步骤2: 遍历每个构件，查找附近的文本
        for comp_data in components:
            # 🔧 兼容性修复：获取构件边界框
            if hasattr(comp_data, 'position'):
                # Pydantic模型格式
                comp_bbox = getattr(comp_data.position, 'bbox_global', None)
            else:
                # 字典格式
                pos = comp_data.get("position", {})
                comp_bbox = pos.get("bbox_global") if isinstance(pos, dict) else getattr(pos, 'bbox_global', None)
                
            if not comp_bbox:
                continue

            comp_center_x = (comp_bbox[0] + comp_bbox[2]) / 2
            comp_center_y = (comp_bbox[1] + comp_bbox[3]) / 2
            
            # 定义搜索半径（例如，构件对角线长度的一半）
            search_radius = math.sqrt((comp_bbox[2] - comp_bbox[0])**2 + (comp_bbox[3] - comp_bbox[1])**2) / 2
            search_radius = max(search_radius, 150) # 设置一个最小搜索半径
            
            associated_texts = []
            
            # 确定要搜索的网格范围
            min_grid_x = int((comp_center_x - search_radius) // grid_size)
            max_grid_x = int((comp_center_x + search_radius) // grid_size)
            min_grid_y = int((comp_center_y - search_radius) // grid_size)
            max_grid_y = int((comp_center_y + search_radius) // grid_size)

            # 在相关网格中搜索
            for gx in range(min_grid_x, max_grid_x + 1):
                for gy in range(min_grid_y, max_grid_y + 1):
                    if (gx, gy) in ocr_grid:
                        for ocr_item in ocr_grid[(gx, gy)]:
                            ocr_bbox = ocr_item.get("bbox")
                            ocr_center_x = (ocr_bbox[0] + ocr_bbox[2]) / 2
                            ocr_center_y = (ocr_bbox[1] + ocr_bbox[3]) / 2
                            
                            # 计算距离
                            distance = math.sqrt((comp_center_x - ocr_center_x)**2 + (comp_center_y - ocr_center_y)**2)
                            
                            if distance <= search_radius:
                                associated_texts.append({
                                    "text": ocr_item.get("text"),
                                    "distance": distance,
                                    "raw_ocr": ocr_item
                                })
            
            # 按距离排序，最近的优先
            associated_texts.sort(key=lambda x: x["distance"])
            
            # 填充 text_tags 和 raw_ocr_texts
            # 🔧 兼容性修复：设置关联文本
            if hasattr(comp_data, '__dict__'):
                # Pydantic模型或对象格式
                comp_data.text_tags = [item["text"] for item in associated_texts]
                comp_data.raw_ocr_texts = [item["raw_ocr"] for item in associated_texts]
            else:
                # 字典格式
                comp_data["text_tags"] = [item["text"] for item in associated_texts]
                comp_data["raw_ocr_texts"] = [item["raw_ocr"] for item in associated_texts]

            try:
                # 🔧 兼容性修复：转换为DrawingComponent
                if hasattr(comp_data, '__dict__') and not isinstance(comp_data, dict):
                    # 已经是对象格式，直接使用
                    final_component_models.append(comp_data)
                else:
                    # 字典格式，需要转换
                    # 类型转换
                    if isinstance(comp_data.get("position"), dict):
                        comp_data["position"] = ComponentPosition(**comp_data["position"])
                    if "geometry" in comp_data and isinstance(comp_data["geometry"], dict):
                        comp_data["geometry"] = ComponentGeometry(**comp_data["geometry"])
                    
                    # 🔧 修复：正确处理confidence字段
                    if isinstance(comp_data.get("confidence"), dict):
                        confidence_data = comp_data["confidence"]
                        # 如果只有overall字段，转换为fusion_confidence
                        if "overall" in confidence_data and "fusion_confidence" not in confidence_data:
                            confidence_data["fusion_confidence"] = confidence_data.pop("overall")
                        comp_data["confidence"] = ComponentConfidence(**confidence_data)
                    
                    # 🔧 修复：字段名映射
                    drawing_component_data = {
                        "id": comp_data.get("id", "unknown"),
                        "component_type": comp_data.get("type", "unknown"),
                        "component_id": comp_data.get("id"),
                        "position": comp_data["position"],
                        "text_tags": comp_data.get("text_tags", []),
                        "geometry": comp_data.get("geometry"),
                        "source_modules": ["Vision", "OCR"],
                        "confidence": comp_data.get("confidence"),
                        "raw_ocr_texts": comp_data.get("raw_ocr_texts", [])
                    }
                    
                    # 使用更新后的数据创建Pydantic模型
                    final_component_models.append(DrawingComponent(**drawing_component_data))
            except Exception as e:
                logger.error(f"无法将构件数据转换为DrawingComponent模型: {e} - 数据: {comp_data}")
        return final_component_models 