import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class AnalysisReportGenerator:
    """
    分析报告生成器
    负责将最终的分析结果格式化，生成前端展示所需的JSON数据和工程量清单。
    """

    def generate_ocr_display(self, global_overview: Dict, total_slices: int) -> Dict[str, Any]:
        """生成OCR识别显示块"""
        if not global_overview:
            global_overview = {}
            
        return {
            "drawing_basic_info": global_overview.get("drawing_info", {}),
            "component_overview": {
                "component_ids": global_overview.get("component_ids", []),
                "component_types": global_overview.get("component_types", []),
                "material_grades": global_overview.get("material_grades", []),
                "axis_lines": global_overview.get("axis_lines", []),
                "summary": global_overview.get("summary", {})
            },
            "ocr_source_info": {
                "total_slices": total_slices,
                "analysis_method": "基于智能切片OCR汇总的GPT分析",
                "slice_reused": True
            }
        }

    def generate_quantity_list_display(self, final_components: List[Dict]) -> Dict[str, Any]:
        """生成工程量清单显示数据"""
        if not final_components:
            return {"success": False, "message": "暂无构件数据", "components": [], "summary": {}}

        table_data = []
        component_stats = {}
        total_volume = 0.0
        total_area = 0.0

        for comp in final_components:
            # This part needs to be adapted to the new unified component schema
            comp_type = comp.get("component_type", "未知")
            raw_vision = comp.get("raw_vision_data", {})
            geometry = raw_vision.get('geometry', {})
            dimensions = geometry.get('dimensions', {})
            
            length = self._extract_dimension_value(dimensions.get('length', '0'))
            width = self._extract_dimension_value(dimensions.get('width', '0'))
            height = self._extract_dimension_value(dimensions.get('height', '0'))
            thickness = self._extract_dimension_value(dimensions.get('thickness', '0'))

            area = self._calculate_area(comp_type, length, width, height, thickness)
            volume = self._calculate_volume(comp_type, length, width, height, thickness)

            table_row = {
                "key": comp.get("id", f"comp_{len(table_data)}"),
                "component_id": comp.get("component_id", '-'),
                "component_type": comp_type,
                "dimensions": self._format_dimensions(length, width, height, thickness),
                "material": raw_vision.get('material', '-'),
                "area": f"{area:.2f}" if area > 0 else '-',
                "volume": f"{volume:.3f}" if volume > 0 else '-',
                "confidence": f"{comp.get('confidence', {}).get('fusion_confidence', 0):.1%}",
            }
            table_data.append(table_row)

            # Statistics
            stats = component_stats.setdefault(comp_type, {"count": 0, "volume": 0.0, "area": 0.0})
            stats["count"] += 1
            stats["volume"] += volume
            stats["area"] += area
            total_volume += volume
            total_area += area

        summary = {
            "total_components": len(final_components),
            "component_types": len(component_stats),
            "total_volume": f"{total_volume:.3f}m³",
            "total_area": f"{total_area:.2f}m²",
            "component_breakdown": component_stats
        }

        return {"success": True, "components": table_data, "summary": summary}

    def _extract_dimension_value(self, dimension_str: Any) -> float:
        """从尺寸字符串中提取数值（mm转换为m）"""
        try:
            if not dimension_str or dimension_str == '-': return 0.0
            numbers = re.findall(r'\d+\.?\d*', str(dimension_str))
            if numbers:
                value = float(numbers[0])
                return value / 1000.0 if 'mm' in str(dimension_str) else value
            return 0.0
        except:
            return 0.0

    def _calculate_area(self, comp_type: str, l: float, w: float, h: float, t: float) -> float:
        """根据构件类型计算面积"""
        comp_type = comp_type.lower()
        if '板' in comp_type or 'slab' in comp_type: return l * w
        if '墙' in comp_type or 'wall' in comp_type: return l * h
        if any(x in comp_type for x in ['梁', 'beam', '柱', 'column']): return w * h
        return 0.0

    def _calculate_volume(self, comp_type: str, l: float, w: float, h: float, t: float) -> float:
        """根据构件类型计算体积"""
        comp_type = comp_type.lower()
        if '板' in comp_type or 'slab' in comp_type: return l * w * (t or h)
        if '墙' in comp_type or 'wall' in comp_type: return l * h * (t or w)
        if '梁' in comp_type or 'beam' in comp_type: return l * w * h
        if '柱' in comp_type or 'column' in comp_type: return (w * h) * (l or t)
        return 0.0

    def _format_dimensions(self, l: float, w: float, h: float, t: float) -> str:
        """格式化尺寸显示"""
        dims = []
        if l > 0: dims.append(f"L{l*1000:.0f}")
        if w > 0: dims.append(f"W{w*1000:.0f}")
        if h > 0: dims.append(f"H{h*1000:.0f}")
        if t > 0 and t != h: dims.append(f"T{t*1000:.0f}")
        return "×".join(dims) if dims else "-" 