#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别结果到工程量计算的转换器
将构件检测结果转换为工程量计算器可处理的格式
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class RecognitionToQuantityConverter:
    """识别结果到工程量计算的转换器"""
    
    def __init__(self):
        # 默认构件参数（单位：mm）
        self.default_params = {
            "walls": {
                "thickness": 200,  # 默认墙厚200mm
                "height": 3000,    # 默认层高3m
                "material": "C30混凝土"
            },
            "columns": {
                "height": 3000,    # 默认柱高3m
                "material": "C30混凝土"
            },
            "beams": {
                "material": "C30混凝土"
            },
            "slabs": {
                "thickness": 120,  # 默认板厚120mm
                "material": "C30混凝土"
            },
            "foundations": {
                "material": "C30混凝土"
            }
        }
    
    def convert_recognition_results(self, recognition_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        将识别结果转换为工程量计算器可处理的格式
        
        Args:
            recognition_results: 构件检测结果
            
        Returns:
            转换后的结果，可直接用于工程量计算
        """
        try:
            converted_results = {
                "walls": [],
                "columns": [],
                "beams": [],
                "slabs": [],
                "foundations": []
            }
            
            # 转换墙体
            if "walls" in recognition_results:
                converted_results["walls"] = self._convert_walls(recognition_results["walls"])
            
            # 转换柱子
            if "columns" in recognition_results:
                converted_results["columns"] = self._convert_columns(recognition_results["columns"])
            
            # 转换梁
            if "beams" in recognition_results:
                converted_results["beams"] = self._convert_beams(recognition_results["beams"])
            
            # 转换板
            if "slabs" in recognition_results:
                converted_results["slabs"] = self._convert_slabs(recognition_results["slabs"])
            
            # 转换基础
            if "foundations" in recognition_results:
                converted_results["foundations"] = self._convert_foundations(recognition_results["foundations"])
            
            logger.info(f"转换完成: 墙体{len(converted_results['walls'])}个, "
                       f"柱子{len(converted_results['columns'])}个, "
                       f"梁{len(converted_results['beams'])}个, "
                       f"板{len(converted_results['slabs'])}个, "
                       f"基础{len(converted_results['foundations'])}个")
            
            return converted_results
            
        except Exception as e:
            logger.error(f"转换识别结果时出错: {str(e)}")
            return {
                "walls": [],
                "columns": [],
                "beams": [],
                "slabs": [],
                "foundations": []
            }
    
    def _convert_walls(self, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换墙体数据"""
        converted_walls = []
        
        for i, wall in enumerate(walls):
            try:
                dimensions = wall.get("dimensions", {})
                width = dimensions.get("width", 0) / 1000  # 转换为米
                height = dimensions.get("height", 0) / 1000  # 转换为米
                
                # 对于墙体，通常width是长度，height是高度
                length = max(width, height)  # 取较大值作为长度
                wall_height = min(width, height) if min(width, height) > 0.5 else self.default_params["walls"]["height"] / 1000
                
                # 如果检测到的高度太小，使用默认层高
                if wall_height < 1.0:
                    wall_height = self.default_params["walls"]["height"] / 1000
                
                converted_wall = {
                    "id": f"W{i+1:03d}",
                    "type": "墙体",
                    "material": self.default_params["walls"]["material"],
                    "length": length,
                    "height": wall_height,
                    "thickness": self.default_params["walls"]["thickness"] / 1000,  # 转换为米
                    "confidence": wall.get("confidence", 0.0),
                    "bbox": wall.get("bbox", [])
                }
                
                converted_walls.append(converted_wall)
                
            except Exception as e:
                logger.warning(f"转换墙体{i}时出错: {str(e)}")
                continue
        
        return converted_walls
    
    def _convert_columns(self, columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换柱子数据"""
        converted_columns = []
        
        for i, column in enumerate(columns):
            try:
                dimensions = column.get("dimensions", {})
                width = dimensions.get("width", 0) / 1000  # 转换为米
                height = dimensions.get("height", 0) / 1000  # 转换为米
                
                # 对于柱子，width和height都是截面尺寸
                col_width = width if width > 0 else 0.4  # 默认400mm
                col_length = height if height > 0 else 0.4  # 默认400mm
                col_height = self.default_params["columns"]["height"] / 1000  # 默认层高
                
                converted_column = {
                    "id": f"C{i+1:03d}",
                    "type": "柱子",
                    "material": self.default_params["columns"]["material"],
                    "length": col_length,
                    "width": col_width,
                    "height": col_height,
                    "confidence": column.get("confidence", 0.0),
                    "bbox": column.get("bbox", [])
                }
                
                converted_columns.append(converted_column)
                
            except Exception as e:
                logger.warning(f"转换柱子{i}时出错: {str(e)}")
                continue
        
        return converted_columns
    
    def _convert_beams(self, beams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换梁数据"""
        converted_beams = []
        
        for i, beam in enumerate(beams):
            try:
                dimensions = beam.get("dimensions", {})
                width = dimensions.get("width", 0) / 1000  # 转换为米
                height = dimensions.get("height", 0) / 1000  # 转换为米
                
                # 对于梁，通常width是长度，height是截面高度
                beam_length = max(width, height)  # 取较大值作为长度
                beam_height = min(width, height) if min(width, height) > 0.1 else 0.5  # 默认梁高500mm
                beam_width = 0.25  # 默认梁宽250mm
                
                converted_beam = {
                    "id": f"B{i+1:03d}",
                    "type": "梁",
                    "material": self.default_params["beams"]["material"],
                    "length": beam_length,
                    "width": beam_width,
                    "height": beam_height,
                    "confidence": beam.get("confidence", 0.0),
                    "bbox": beam.get("bbox", [])
                }
                
                converted_beams.append(converted_beam)
                
            except Exception as e:
                logger.warning(f"转换梁{i}时出错: {str(e)}")
                continue
        
        return converted_beams
    
    def _convert_slabs(self, slabs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换板数据"""
        converted_slabs = []
        
        for i, slab in enumerate(slabs):
            try:
                dimensions = slab.get("dimensions", {})
                width = dimensions.get("width", 0) / 1000  # 转换为米
                height = dimensions.get("height", 0) / 1000  # 转换为米
                
                # 对于板，width和height都是平面尺寸
                slab_length = max(width, height) if max(width, height) > 0 else 6.0  # 默认6m
                slab_width = min(width, height) if min(width, height) > 0 else 4.0   # 默认4m
                slab_thickness = self.default_params["slabs"]["thickness"] / 1000    # 转换为米
                
                converted_slab = {
                    "id": f"S{i+1:03d}",
                    "type": "板",
                    "material": self.default_params["slabs"]["material"],
                    "length": slab_length,
                    "width": slab_width,
                    "thickness": slab_thickness,
                    "confidence": slab.get("confidence", 0.0),
                    "bbox": slab.get("bbox", [])
                }
                
                converted_slabs.append(converted_slab)
                
            except Exception as e:
                logger.warning(f"转换板{i}时出错: {str(e)}")
                continue
        
        return converted_slabs
    
    def _convert_foundations(self, foundations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """转换基础数据"""
        converted_foundations = []
        
        for i, foundation in enumerate(foundations):
            try:
                dimensions = foundation.get("dimensions", {})
                width = dimensions.get("width", 0) / 1000  # 转换为米
                height = dimensions.get("height", 0) / 1000  # 转换为米
                
                # 对于基础，width和height是平面尺寸
                found_length = max(width, height) if max(width, height) > 0 else 2.0  # 默认2m
                found_width = min(width, height) if min(width, height) > 0 else 2.0   # 默认2m
                found_height = 0.8  # 默认基础高度800mm
                
                converted_foundation = {
                    "id": f"F{i+1:03d}",
                    "type": "基础",
                    "material": self.default_params["foundations"]["material"],
                    "length": found_length,
                    "width": found_width,
                    "height": found_height,
                    "confidence": foundation.get("confidence", 0.0),
                    "bbox": foundation.get("bbox", [])
                }
                
                converted_foundations.append(converted_foundation)
                
            except Exception as e:
                logger.warning(f"转换基础{i}时出错: {str(e)}")
                continue
        
        return converted_foundations


# 测试代码
if __name__ == "__main__":
    print("🔄 识别结果转换器测试")
    print("=" * 50)
    
    # 创建转换器
    converter = RecognitionToQuantityConverter()
    
    # 模拟识别结果
    test_recognition_results = {
        "walls": [
            {
                "bbox": [100, 100, 500, 150],
                "confidence": 0.85,
                "dimensions": {"width": 12400, "height": 5600},
                "class_name": "wall"
            }
        ],
        "columns": [
            {
                "bbox": [200, 200, 250, 250],
                "confidence": 0.90,
                "dimensions": {"width": 400, "height": 400},
                "class_name": "column"
            }
        ],
        "beams": [
            {
                "bbox": [300, 300, 800, 350],
                "confidence": 0.75,
                "dimensions": {"width": 6000, "height": 500},
                "class_name": "beam"
            }
        ]
    }
    
    # 执行转换
    converted_results = converter.convert_recognition_results(test_recognition_results)
    
    # 显示结果
    print("\n📊 转换结果:")
    for component_type, components in converted_results.items():
        if components:
            print(f"\n{component_type.upper()}:")
            for comp in components:
                print(f"  {comp['id']}: {comp['type']}")
                if 'length' in comp:
                    print(f"    尺寸: {comp.get('length', 0):.2f}m × {comp.get('width', comp.get('thickness', 0)):.2f}m × {comp.get('height', comp.get('thickness', 0)):.2f}m")
                print(f"    置信度: {comp['confidence']:.2f}")
    
    print("\n✅ 转换器测试完成！") 