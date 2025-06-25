# -*- coding: utf-8 -*-
"""
通用工具管理器：负责尺寸提取、面积体积计算、单位换算等
"""
import logging
from typing import Any
import re

logger = logging.getLogger(__name__)

class UtilsManager:
    """
    通用工具管理器：负责尺寸提取、面积体积计算、单位换算等
    """
    def __init__(self, analyzer):
        self.analyzer = analyzer

    def extract_dimension_value(self, dimension_str: str) -> float:
        """
        从尺寸字符串中提取数值（mm转换为m）
        :param dimension_str: 尺寸字符串，如 '200mm' 或 '2.5'
        :return: 浮点数，单位为米
        """
        try:
            if not dimension_str or dimension_str == '-':
                return 0.0
            numbers = re.findall(r'\d+\.?\d*', str(dimension_str))
            if numbers:
                value = float(numbers[0])
                if 'mm' in str(dimension_str):
                    return value / 1000.0
                return value
            return 0.0
        except:
            return 0.0

    def calculate_area(self, comp_type: str, length: float, width: float, height: float, thickness: float) -> float:
        """
        根据构件类型计算面积
        :return: 面积，单位平方米
        """
        try:
            comp_type_lower = comp_type.lower()
            if '板' in comp_type or 'slab' in comp_type_lower:
                return length * width if length > 0 and width > 0 else 0.0
            elif '墙' in comp_type or 'wall' in comp_type_lower:
                return length * height if length > 0 and height > 0 else 0.0
            elif '梁' in comp_type or 'beam' in comp_type_lower:
                return width * height if width > 0 and height > 0 else 0.0
            elif '柱' in comp_type or 'column' in comp_type_lower:
                return width * height if width > 0 and height > 0 else 0.0
            else:
                dims = [d for d in [length, width, height, thickness] if d > 0]
                if len(dims) >= 2:
                    dims.sort(reverse=True)
                    return dims[0] * dims[1]
                return 0.0
        except:
            return 0.0

    def calculate_volume(self, comp_type: str, length: float, width: float, height: float, thickness: float) -> float:
        """
        根据构件类型计算体积
        :return: 体积，单位立方米
        """
        try:
            comp_type_lower = comp_type.lower()
            if '板' in comp_type or 'slab' in comp_type_lower:
                thick = thickness or height
                return length * width * thick if length > 0 and width > 0 and thick > 0 else 0.0
            elif '墙' in comp_type or 'wall' in comp_type_lower:
                thick = thickness or width
                return length * height * thick if length > 0 and height > 0 and thick > 0 else 0.0
            elif '梁' in comp_type or 'beam' in comp_type_lower:
                return length * width * height if length > 0 and width > 0 and height > 0 else 0.0
            elif '柱' in comp_type or 'column' in comp_type_lower:
                section_area = width * height if width > 0 and height > 0 else 0.0
                col_height = length or thickness
                return section_area * col_height if section_area > 0 and col_height > 0 else 0.0
            else:
                dims = [d for d in [length, width, height, thickness] if d > 0]
                if len(dims) >= 3:
                    return dims[0] * dims[1] * dims[2]
                return 0.0
        except:
            return 0.0

    def format_dimensions(self, length: float, width: float, height: float, thickness: float) -> str:
        """
        格式化尺寸显示
        :return: 形如 L2000×W300×H500 的字符串
        """
        try:
            dims = []
            if length > 0:
                dims.append(f"L{length*1000:.0f}")
            if width > 0:
                dims.append(f"W{width*1000:.0f}")
            if height > 0:
                dims.append(f"H{height*1000:.0f}")
            if thickness > 0 and thickness != height:
                dims.append(f"T{thickness*1000:.0f}")
            return "×".join(dims) if dims else "-"
        except:
            return "-" 