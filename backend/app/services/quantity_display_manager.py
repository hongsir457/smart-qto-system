# -*- coding: utf-8 -*-
"""
工程量清单显示管理器：负责工程量清单生成、OCR识别结果展示等
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class QuantityDisplayManager:
    """
    工程量清单显示管理器：负责工程量清单生成、OCR识别结果展示等
    """
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def generate_quantity_list_display(self) -> Dict[str, Any]:
        """
        生成工程量清单显示数据（基于Vision汇总的构件几何数据）
        :return: 包含表格数据、汇总信息和表头定义的字典
        """
        try:
            if not self.analyzer.merged_components:
                return {
                    "success": False,
                    "message": "暂无构件数据",
                    "components": [],
                    "summary": {}
                }
            table_data = []
            component_stats = {}
            total_volume = 0.0
            total_area = 0.0
            for comp in self.analyzer.merged_components:
                geometry = getattr(comp, 'geometry', {}) if hasattr(comp, 'geometry') else {}
                dimensions = geometry.get('dimensions', {})
                # 解析尺寸字符串获取数值
                length = self.analyzer.utils_manager.extract_dimension_value(dimensions.get('length', '0'))
                width = self.analyzer.utils_manager.extract_dimension_value(dimensions.get('width', '0'))
                height = self.analyzer.utils_manager.extract_dimension_value(dimensions.get('height', '0'))
                thickness = self.analyzer.utils_manager.extract_dimension_value(dimensions.get('thickness', '0'))
                # 计算面积和体积
                area = self.analyzer.utils_manager.calculate_area(comp.type, length, width, height, thickness)
                volume = self.analyzer.utils_manager.calculate_volume(comp.type, length, width, height, thickness)
                structural_role = getattr(comp, 'structural_role', '未知') if hasattr(comp, 'structural_role') else '未知'
                connections = getattr(comp, 'connections', []) if hasattr(comp, 'connections') else []
                connections_str = ', '.join(connections) if connections else '-'
                table_row = {
                    "key": comp.id or f"comp_{len(table_data)}",
                    "component_id": comp.id or '-',
                    "component_type": comp.type,
                    "dimensions": self.analyzer.utils_manager.format_dimensions(length, width, height, thickness),
                    "material": comp.material or '-',
                    "area": f"{area:.2f}" if area > 0 else '-',
                    "volume": f"{volume:.3f}" if volume > 0 else '-',
                    "structural_role": structural_role,
                    "connections": connections_str,
                    "location": comp.location or '-',
                    "confidence": f"{comp.confidence:.1%}" if hasattr(comp, 'confidence') else '-',
                    "source_slice": comp.source_block or '-'
                }
                table_data.append(table_row)
                comp_type = comp.type
                if comp_type not in component_stats:
                    component_stats[comp_type] = {"count": 0, "volume": 0.0, "area": 0.0}
                component_stats[comp_type]["count"] += 1
                component_stats[comp_type]["volume"] += volume
                component_stats[comp_type]["area"] += area
                total_volume += volume
                total_area += area
            summary = {
                "total_components": len(self.analyzer.merged_components),
                "component_types": len(component_stats),
                "total_volume": f"{total_volume:.3f}m³",
                "total_area": f"{total_area:.2f}m²",
                "component_breakdown": component_stats,
                "analysis_source": "基于Vision构件识别的几何数据汇总"
            }
            logger.info(f"✅ 工程量清单显示数据生成完成: {len(table_data)} 个构件")
            return {
                "success": True,
                "components": table_data,
                "summary": summary,
                "table_columns": [
                    {"title": "构件编号", "dataIndex": "component_id", "key": "component_id", "width": 120},
                    {"title": "构件类型", "dataIndex": "component_type", "key": "component_type", "width": 100},
                    {"title": "尺寸规格", "dataIndex": "dimensions", "key": "dimensions", "width": 150},
                    {"title": "材料", "dataIndex": "material", "key": "material", "width": 100},
                    {"title": "面积(m²)", "dataIndex": "area", "key": "area", "width": 100},
                    {"title": "体积(m³)", "dataIndex": "volume", "key": "volume", "width": 100},
                    {"title": "结构作用", "dataIndex": "structural_role", "key": "structural_role", "width": 100},
                    {"title": "连接构件", "dataIndex": "connections", "key": "connections", "width": 120},
                    {"title": "置信度", "dataIndex": "confidence", "key": "confidence", "width": 80}
                ]
            }
        except Exception as e:
            logger.error(f"❌ 生成工程量清单显示数据失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "components": [],
                "summary": {}
            }

    def generate_ocr_recognition_display(self) -> Dict[str, Any]:
        """
        生成OCR识别结果展示数据（图纸基本信息和构件信息）
        :return: 包含图纸信息、构件概览、OCR来源信息的字典
        """
        try:
            overview = getattr(self.analyzer, 'global_drawing_overview', {})
            enhanced_slices = getattr(self.analyzer, 'enhanced_slices', [])
            ocr_text_count = len(overview.get("component_ids", [])) if overview else 0
            return {
                "drawing_basic_info": overview.get("drawing_info", {}) if overview else {},
                "component_overview": {
                    "component_ids": overview.get("component_ids", []) if overview else [],
                    "component_types": overview.get("component_types", []) if overview else [],
                    "material_grades": overview.get("material_grades", []) if overview else [],
                    "axis_lines": overview.get("axis_lines", []) if overview else [],
                    "summary": overview.get("summary", {}) if overview else {}
                },
                "ocr_source_info": {
                    "total_slices": len(enhanced_slices),
                    "ocr_text_count": ocr_text_count,
                    "analysis_method": "基于智能切片OCR汇总的GPT分析",
                    "slice_reused": True
                }
            }
        except Exception as e:
            logger.error(f"❌ 生成OCR识别结果展示数据失败: {e}")
            return {
                "drawing_basic_info": {},
                "component_overview": {},
                "ocr_source_info": {}
            } 