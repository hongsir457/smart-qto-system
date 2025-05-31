from typing import Dict, Any, List
import math

class QuantityCalculator:
    @staticmethod
    def calculate_volume(length: float, width: float, height: float) -> float:
        """计算体积"""
        return length * width * height

    @staticmethod
    def calculate_area(length: float, width: float) -> float:
        """计算面积"""
        return length * width

    @staticmethod
    def calculate_wall_quantity(length: float, height: float, thickness: float) -> Dict[str, float]:
        """计算墙体工程量"""
        volume = length * height * thickness
        area = length * height
        return {
            "volume": volume,  # 体积
            "area": area,      # 面积
            "length": length   # 长度
        }

    @staticmethod
    def calculate_column_quantity(length: float, width: float, height: float) -> Dict[str, float]:
        """计算柱子工程量"""
        volume = length * width * height
        return {
            "volume": volume,  # 体积
            "area": length * width,  # 截面面积
            "height": height   # 高度
        }

    @staticmethod
    def calculate_beam_quantity(length: float, width: float, height: float) -> Dict[str, float]:
        """计算梁工程量"""
        volume = length * width * height
        return {
            "volume": volume,  # 体积
            "length": length,  # 长度
            "area": width * height  # 截面面积
        }

    @staticmethod
    def calculate_slab_quantity(length: float, width: float, thickness: float) -> Dict[str, float]:
        """计算板工程量"""
        volume = length * width * thickness
        area = length * width
        return {
            "volume": volume,  # 体积
            "area": area,      # 面积
            "thickness": thickness  # 厚度
        }

    @staticmethod
    def calculate_foundation_quantity(length: float, width: float, height: float) -> Dict[str, float]:
        """计算基础工程量"""
        volume = length * width * height
        return {
            "volume": volume,  # 体积
            "area": length * width,  # 底面积
            "height": height   # 高度
        }

    @staticmethod
    def process_recognition_results(results: Dict[str, Any]) -> Dict[str, Any]:
        """处理识别结果并计算工程量"""
        quantities = {
            "walls": [],
            "columns": [],
            "beams": [],
            "slabs": [],
            "foundations": [],
            "total": {
                "wall_volume": 0,
                "column_volume": 0,
                "beam_volume": 0,
                "slab_volume": 0,
                "foundation_volume": 0,
                "total_volume": 0
            }
        }

        # 处理墙体
        for wall in results.get("walls", []):
            wall_quantity = QuantityCalculator.calculate_wall_quantity(
                wall["length"],
                wall["height"],
                wall["thickness"]
            )
            quantities["walls"].append({
                "id": wall["id"],
                "type": wall["type"],
                "material": wall["material"],
                "quantities": wall_quantity
            })
            quantities["total"]["wall_volume"] += wall_quantity["volume"]

        # 处理柱子
        for column in results.get("columns", []):
            column_quantity = QuantityCalculator.calculate_column_quantity(
                column["length"],
                column["width"],
                column["height"]
            )
            quantities["columns"].append({
                "id": column["id"],
                "type": column["type"],
                "material": column["material"],
                "quantities": column_quantity
            })
            quantities["total"]["column_volume"] += column_quantity["volume"]

        # 处理梁
        for beam in results.get("beams", []):
            beam_quantity = QuantityCalculator.calculate_beam_quantity(
                beam["length"],
                beam["width"],
                beam["height"]
            )
            quantities["beams"].append({
                "id": beam["id"],
                "type": beam["type"],
                "material": beam["material"],
                "quantities": beam_quantity
            })
            quantities["total"]["beam_volume"] += beam_quantity["volume"]

        # 处理板
        for slab in results.get("slabs", []):
            slab_quantity = QuantityCalculator.calculate_slab_quantity(
                slab["length"],
                slab["width"],
                slab["thickness"]
            )
            quantities["slabs"].append({
                "id": slab["id"],
                "type": slab["type"],
                "material": slab["material"],
                "quantities": slab_quantity
            })
            quantities["total"]["slab_volume"] += slab_quantity["volume"]

        # 处理基础
        for foundation in results.get("foundations", []):
            foundation_quantity = QuantityCalculator.calculate_foundation_quantity(
                foundation["length"],
                foundation["width"],
                foundation["height"]
            )
            quantities["foundations"].append({
                "id": foundation["id"],
                "type": foundation["type"],
                "material": foundation["material"],
                "quantities": foundation_quantity
            })
            quantities["total"]["foundation_volume"] += foundation_quantity["volume"]

        # 计算总体积
        quantities["total"]["total_volume"] = (
            quantities["total"]["wall_volume"] +
            quantities["total"]["column_volume"] +
            quantities["total"]["beam_volume"] +
            quantities["total"]["slab_volume"] +
            quantities["total"]["foundation_volume"]
        )

        return quantities 