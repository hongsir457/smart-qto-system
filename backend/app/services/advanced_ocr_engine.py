#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级OCR引擎 - 建筑图纸专用
集成PaddleOCR，支持构件符号识别和尺寸标注提取
"""

import cv2
import numpy as np
import re
import json
from typing import Dict, List, Any, Tuple, Optional
import logging

# 配置日志
logger = logging.getLogger(__name__)

class AdvancedOCREngine:
    """建筑图纸专用OCR引擎"""
    
    def __init__(self):
        """初始化OCR引擎"""
        self.text_ocr = None
        self.component_symbols = self._load_component_symbols()
        self.dimension_patterns = self._load_dimension_patterns()
        
        # 尝试加载PaddleOCR
        try:
            from paddleocr import PaddleOCR
            self.text_ocr = PaddleOCR(
                use_angle_cls=True, 
                lang='ch',  # 支持中英文
                show_log=False
            )
            print("✅ PaddleOCR加载成功")
        except ImportError:
            print("⚠️  PaddleOCR未安装，请运行: pip install paddlepaddle paddleocr")
            print("   将使用演示模式")
        except Exception as e:
            print(f"⚠️  PaddleOCR加载失败: {str(e)}")
            print("   将使用演示模式")
    
    def _load_component_symbols(self) -> Dict[str, str]:
        """加载构件符号映射表"""
        return {
            # 柱子符号 (Columns)
            "KZ": "框架柱",
            "XZ": "芯柱", 
            "LZ": "梁上柱",
            "QZ": "剪力墙边缘构件",
            "YZ": "约束边缘构件",
            "GZ": "构造边缘构件",
            "JZ": "独立柱",
            
            # 梁符号 (Beams)
            "KL": "框架梁",
            "LL": "连梁",
            "WKL": "屋面框架梁",
            "JL": "基础梁",
            "XL": "小梁",
            "AL": "暗梁",
            "YKL": "雨篷梁",
            "RGL": "绕管梁",
            
            # 板符号 (Slabs)
            "LB": "楼板",
            "WB": "屋面板",
            "YXB": "预应力板",
            "PB": "平板",
            "DB": "吊板",
            "RB": "悬挑板",
            
            # 墙符号 (Walls)
            "Q": "剪力墙",
            "FQ": "非承重墙",
            "DQ": "挡土墙",
            "WQ": "围墙",
            
            # 基础符号 (Foundations)
            "DJJ": "独立基础",
            "CFJ": "筏板基础",
            "DTJ": "条形基础",
            "ZJ": "桩基础",
            "BWJ": "杯型基础",
            
            # 楼梯符号 (Stairs)
            "LT": "楼梯",
            "JT": "夹层楼梯",
            "XT": "悬挑楼梯",
            
            # 其他构件
            "PM": "飘窗",
            "TC": "凸窗",
            "YP": "雨篷",
            "XB": "挑板",
        }
    
    def _load_dimension_patterns(self) -> List[str]:
        """加载尺寸标注模式"""
        return [
            r'(\d+(?:\.\d+)?)\s*(?:mm|MM)?',  # 数字+可选单位
            r'(\d+)×(\d+)',  # 长×宽格式
            r'(\d+)\s*[xX]\s*(\d+)',  # 长x宽格式
            r'φ(\d+(?:\.\d+)?)',  # 直径符号
            r'Φ(\d+(?:\.\d+)?)',  # 直径符号（大写）
            r'R(\d+(?:\.\d+)?)',  # 半径
            r'(\d+)-(\d+)',  # 范围表示
        ]
    
    def extract_text_and_symbols(self, image_path: str) -> Dict[str, Any]:
        """提取图纸中的文字和符号
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            Dict: 包含文字、符号、构件编号等信息
        """
        try:
            # 读取图像
            if isinstance(image_path, str):
                image = cv2.imread(image_path)
            else:
                image = image_path  # 如果直接传入图像数组
            
            if image is None:
                raise ValueError(f"无法读取图像: {image_path}")
            
            # 如果OCR未加载，返回演示数据
            if self.text_ocr is None:
                return self._generate_demo_ocr_results(image_path)
            
            # 执行OCR识别
            ocr_results = self.text_ocr.ocr(image, cls=True)
            
            # 处理OCR结果
            processed_results = self._process_ocr_results(ocr_results)
            
            # 提取构件编号
            component_codes = self._extract_component_codes(processed_results)
            
            # 提取尺寸标注
            dimensions = self._extract_dimensions(processed_results)
            
            # 识别材料信息
            materials = self._extract_material_info(processed_results)
            
            return {
                "raw_ocr_results": ocr_results,
                "processed_texts": processed_results,
                "component_codes": component_codes,
                "dimensions": dimensions,
                "materials": materials,
                "statistics": {
                    "total_texts": len(processed_results),
                    "component_count": len(component_codes),
                    "dimension_count": len(dimensions),
                    "material_count": len(materials)
                }
            }
            
        except Exception as e:
            logger.error(f"OCR识别过程出错: {str(e)}")
            return self._generate_demo_ocr_results(image_path)
    
    def _process_ocr_results(self, ocr_results: List) -> List[Dict[str, Any]]:
        """处理原始OCR结果"""
        processed = []
        
        if not ocr_results or not ocr_results[0]:
            return processed
        
        for line in ocr_results[0]:
            if not line or len(line) < 2:
                continue
                
            bbox = line[0]  # 边界框坐标
            text_info = line[1]  # (文字, 置信度)
            
            if not text_info or len(text_info) < 2:
                continue
                
            text = text_info[0].strip()
            confidence = text_info[1]
            
            # 过滤太短或置信度太低的文字
            if len(text) < 1 or confidence < 0.3:
                continue
            
            # 计算文字位置中心点
            bbox_array = np.array(bbox)
            center_x = int(np.mean(bbox_array[:, 0]))
            center_y = int(np.mean(bbox_array[:, 1]))
            
            processed.append({
                "text": text,
                "confidence": confidence,
                "bbox": bbox,
                "center": (center_x, center_y),
                "width": int(np.max(bbox_array[:, 0]) - np.min(bbox_array[:, 0])),
                "height": int(np.max(bbox_array[:, 1]) - np.min(bbox_array[:, 1]))
            })
        
        return processed
    
    def _extract_component_codes(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取构件编号（如KZ1、KL2等）"""
        component_codes = []
        
        # 构件编号正则模式
        patterns = [
            r'([A-Z]{1,3})(\d+[A-Z]?)',  # KZ1, KL2A等
            r'([A-Z]{1,3})-(\d+)',       # KZ-1等
            r'([A-Z]{1,3})\.(\d+)',      # KZ.1等
        ]
        
        for text_info in texts:
            text = text_info['text'].upper()  # 转为大写
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    symbol = match[0]
                    number = match[1]
                    
                    # 检查是否为已知构件符号
                    if symbol in self.component_symbols:
                        component_codes.append({
                            "symbol": symbol,
                            "number": number,
                            "full_code": f"{symbol}{number}",
                            "type": self.component_symbols[symbol],
                            "position": text_info['center'],
                            "bbox": text_info['bbox'],
                            "confidence": text_info['confidence'],
                            "source_text": text_info['text']
                        })
        
        return component_codes
    
    def _extract_dimensions(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取尺寸标注"""
        dimensions = []
        
        for text_info in texts:
            text = text_info['text']
            
            # 尝试各种尺寸模式
            for pattern in self.dimension_patterns:
                matches = re.findall(pattern, text)
                
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            # 处理多个值的情况（如长×宽）
                            if len(match) == 2:
                                dimensions.append({
                                    "type": "dimension_pair",
                                    "values": [float(match[0]), float(match[1])],
                                    "unit": self._extract_unit(text),
                                    "position": text_info['center'],
                                    "bbox": text_info['bbox'],
                                    "confidence": text_info['confidence'],
                                    "source_text": text_info['text']
                                })
                        else:
                            # 单个值
                            try:
                                value = float(match)
                                dimensions.append({
                                    "type": "single_dimension",
                                    "value": value,
                                    "unit": self._extract_unit(text),
                                    "position": text_info['center'],
                                    "bbox": text_info['bbox'],
                                    "confidence": text_info['confidence'],
                                    "source_text": text_info['text']
                                })
                            except ValueError:
                                continue
        
        return dimensions
    
    def _extract_unit(self, text: str) -> str:
        """从文本中提取单位"""
        text_upper = text.upper()
        if 'MM' in text_upper or 'mm' in text:
            return 'mm'
        elif 'M' in text_upper and 'm' in text:
            return 'm'
        elif 'CM' in text_upper or 'cm' in text:
            return 'cm'
        else:
            return 'mm'  # 默认单位
    
    def _extract_material_info(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取材料信息"""
        materials = []
        
        # 常见材料模式
        material_patterns = {
            r'C(\d+)': 'concrete_grade',  # 混凝土等级 C30, C35等
            r'HRB(\d+)': 'rebar_grade',   # 钢筋等级 HRB400, HRB500等
            r'HPB(\d+)': 'rebar_grade',   # 钢筋等级 HPB300等
            r'Q(\d+)': 'steel_grade',     # 钢材等级 Q235, Q345等
        }
        
        for text_info in texts:
            text = text_info['text'].upper()
            
            for pattern, material_type in material_patterns.items():
                matches = re.findall(pattern, text)
                for match in matches:
                    materials.append({
                        "type": material_type,
                        "grade": match,
                        "full_name": text_info['text'],
                        "position": text_info['center'],
                        "bbox": text_info['bbox'],
                        "confidence": text_info['confidence']
                    })
        
        return materials
    
    def _generate_demo_ocr_results(self, image_path: str) -> Dict[str, Any]:
        """生成演示OCR结果（当OCR引擎不可用时）"""
        import random
        import hashlib
        
        # 基于文件路径生成稳定的随机数种子
        if isinstance(image_path, str):
            seed = int(hashlib.md5(image_path.encode()).hexdigest()[:8], 16)
        else:
            seed = 12345
        random.seed(seed)
        
        # 生成演示构件编号
        demo_components = []
        component_types = list(self.component_symbols.keys())[:8]  # 取前8种
        
        for i, symbol in enumerate(component_types):
            demo_components.append({
                "symbol": symbol,
                "number": str(random.randint(1, 5)),
                "full_code": f"{symbol}{random.randint(1, 5)}",
                "type": self.component_symbols[symbol],
                "position": (random.randint(100, 600), random.randint(100, 400)),
                "bbox": [[100, 100], [200, 100], [200, 150], [100, 150]],
                "confidence": random.uniform(0.85, 0.95),
                "source_text": f"{symbol}{random.randint(1, 5)}"
            })
        
        # 生成演示尺寸
        demo_dimensions = []
        for i in range(random.randint(5, 10)):
            if random.choice([True, False]):
                # 单一尺寸
                demo_dimensions.append({
                    "type": "single_dimension",
                    "value": random.randint(200, 8000),
                    "unit": "mm",
                    "position": (random.randint(100, 700), random.randint(100, 500)),
                    "bbox": [[100, 100], [200, 100], [200, 150], [100, 150]],
                    "confidence": random.uniform(0.8, 0.95),
                    "source_text": f"{random.randint(200, 8000)}"
                })
            else:
                # 尺寸对
                w, h = random.randint(200, 500), random.randint(300, 800)
                demo_dimensions.append({
                    "type": "dimension_pair",
                    "values": [w, h],
                    "unit": "mm",
                    "position": (random.randint(100, 700), random.randint(100, 500)),
                    "bbox": [[100, 100], [200, 100], [200, 150], [100, 150]],
                    "confidence": random.uniform(0.8, 0.95),
                    "source_text": f"{w}×{h}"
                })
        
        # 生成演示材料
        demo_materials = []
        material_grades = ['C30', 'C35', 'HRB400', 'HRB500', 'Q235']
        for grade in material_grades[:random.randint(2, 4)]:
            demo_materials.append({
                "type": "concrete_grade" if grade.startswith('C') else 
                       "rebar_grade" if grade.startswith('H') else "steel_grade",
                "grade": grade[1:] if grade[0].isalpha() else grade,
                "full_name": grade,
                "position": (random.randint(100, 700), random.randint(100, 500)),
                "bbox": [[100, 100], [200, 100], [200, 150], [100, 150]],
                "confidence": random.uniform(0.9, 0.98)
            })
        
        return {
            "raw_ocr_results": None,
            "processed_texts": [],
            "component_codes": demo_components,
            "dimensions": demo_dimensions,
            "materials": demo_materials,
            "statistics": {
                "total_texts": len(demo_components) + len(demo_dimensions) + len(demo_materials),
                "component_count": len(demo_components),
                "dimension_count": len(demo_dimensions),
                "material_count": len(demo_materials)
            },
            "demo_mode": True
        }
    
    def get_component_info(self, component_code: str) -> Optional[Dict[str, str]]:
        """根据构件编号获取构件信息"""
        # 解析构件编号
        match = re.match(r'([A-Z]{1,3})(\d+[A-Z]?)', component_code.upper())
        if match:
            symbol = match.group(1)
            number = match.group(2)
            
            if symbol in self.component_symbols:
                return {
                    "symbol": symbol,
                    "number": number,
                    "type": self.component_symbols[symbol],
                    "full_code": component_code.upper()
                }
        return None
    
    def export_ocr_results(self, results: Dict[str, Any], output_path: str = "ocr_results.json"):
        """导出OCR识别结果到JSON文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            print(f"📄 OCR结果已导出到: {output_path}")
        except Exception as e:
            logger.error(f"导出OCR结果失败: {str(e)}")


# 如果直接运行此文件，执行测试
if __name__ == "__main__":
    print("🔍 高级OCR引擎测试")
    print("=" * 50)
    
    # 初始化OCR引擎
    ocr = AdvancedOCREngine()
    
    # 测试构件编号识别
    test_codes = ["KZ1", "KL2", "LB1", "DJJ3", "WKL5"]
    print("\n📋 构件编号识别测试:")
    for code in test_codes:
        info = ocr.get_component_info(code)
        if info:
            print(f"  {code} → {info['type']}")
        else:
            print(f"  {code} → 未知构件")
    
    print("\n✅ OCR引擎初始化完成！")
    print("💡 提示：使用 extract_text_and_symbols(image_path) 方法进行图纸识别") 