#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图集规范识别引擎 - 国标图集符号识别
实现建筑制图标准和国家标准图集的符号识别
"""

import re
import json
import cv2
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# 配置日志
logger = logging.getLogger(__name__)

class AtlasStandard(Enum):
    """图集标准枚举"""
    GB_T_50001 = "GB/T 50001-2017"  # 房屋建筑制图统一标准
    GB_T_50105 = "GB/T 50105-2010"  # 建筑结构制图标准
    GB_50010 = "GB 50010-2010"      # 混凝土结构设计规范
    GB_50011 = "GB 50011-2010"      # 建筑抗震设计规范
    
class ComponentSymbol(Enum):
    """构件符号枚举"""
    # 柱类
    KZ = "框架柱"
    GZ = "构造柱"
    LZ = "梁式柱"
    XZ = "芯柱"
    
    # 梁类
    KL = "框架梁"
    LL = "连梁"
    JL = "基础梁"
    WKL = "屋面框架梁"
    
    # 板类
    LB = "楼板"
    WB = "屋面板"
    YB = "雨篷板"
    
    # 墙类
    Q = "墙"
    JQ = "剪力墙"
    FQ = "分隔墙"
    
    # 基础类
    DJJ = "独立基础"
    TJJ = "条形基础"
    FJJ = "筏形基础"

@dataclass
class AtlasSymbolData:
    """图集符号数据结构"""
    symbol: str                    # 符号代码
    name: str                     # 构件名称
    category: ComponentSymbol     # 构件类别
    standard: AtlasStandard      # 所属标准
    description: str             # 描述
    typical_dimensions: Dict[str, float]  # 典型尺寸
    drawing_rules: List[str]     # 绘图规则
    calculation_rules: List[str] # 计算规则

class AtlasRecognitionEngine:
    """图集规范识别引擎"""
    
    def __init__(self):
        """初始化识别引擎"""
        self.atlas_symbols = self._load_atlas_symbols()
        self.drawing_standards = self._load_drawing_standards()
        self.dimension_patterns = self._load_dimension_patterns()
        self.scale_patterns = self._load_scale_patterns()
        
    def _load_atlas_symbols(self) -> Dict[str, AtlasSymbolData]:
        """加载国标图集符号库"""
        symbols = {}
        
        # 柱类符号
        symbols["KZ"] = AtlasSymbolData(
            symbol="KZ",
            name="框架柱",
            category=ComponentSymbol.KZ,
            standard=AtlasStandard.GB_T_50105,
            description="钢筋混凝土框架结构中的柱子",
            typical_dimensions={"width": 400, "height": 400, "length": 3000},
            drawing_rules=[
                "柱截面用粗实线绘制",
                "柱编号标注在柱中心附近",
                "截面尺寸标注格式：宽×高"
            ],
            calculation_rules=[
                "按GB50500-2013清单规范计算",
                "混凝土按体积计算",
                "扣除梁柱节点重复部分"
            ]
        )
        
        symbols["GZ"] = AtlasSymbolData(
            symbol="GZ",
            name="构造柱",
            category=ComponentSymbol.GZ,
            standard=AtlasStandard.GB_T_50105,
            description="砌体结构中的钢筋混凝土构造柱",
            typical_dimensions={"width": 240, "height": 240, "length": 3000},
            drawing_rules=[
                "用细实线绘制轮廓",
                "内部填充斜线表示钢筋混凝土",
                "与墙体连接处绘制马牙槎"
            ],
            calculation_rules=[
                "按实际体积计算",
                "不扣除墙体嵌入部分"
            ]
        )
        
        # 梁类符号
        symbols["KL"] = AtlasSymbolData(
            symbol="KL",
            name="框架梁",
            category=ComponentSymbol.KL,
            standard=AtlasStandard.GB_T_50105,
            description="钢筋混凝土框架结构中的梁",
            typical_dimensions={"width": 250, "height": 500, "length": 6000},
            drawing_rules=[
                "梁轴线用细点划线绘制",
                "梁截面用粗实线绘制",
                "梁编号标注在梁跨中"
            ],
            calculation_rules=[
                "按净长计算",
                "梁高从板顶算至梁底"
            ]
        )
        
        symbols["LL"] = AtlasSymbolData(
            symbol="LL",
            name="连梁",
            category=ComponentSymbol.LL,
            standard=AtlasStandard.GB_T_50105,
            description="连接剪力墙的梁",
            typical_dimensions={"width": 200, "height": 400, "length": 1500},
            drawing_rules=[
                "连接两片剪力墙",
                "截面较小，跨度较短"
            ],
            calculation_rules=[
                "按净长计算",
                "考虑墙体约束影响"
            ]
        )
        
        # 板类符号
        symbols["LB"] = AtlasSymbolData(
            symbol="LB",
            name="楼板",
            category=ComponentSymbol.LB,
            standard=AtlasStandard.GB_T_50105,
            description="楼层结构板",
            typical_dimensions={"width": 6000, "length": 8000, "thickness": 120},
            drawing_rules=[
                "板边界用粗实线绘制",
                "板厚标注在剖面图中",
                "开洞用细实线表示"
            ],
            calculation_rules=[
                "按净面积计算",
                "扣除大于0.3m²的洞口"
            ]
        )
        
        # 墙类符号
        symbols["Q"] = AtlasSymbolData(
            symbol="Q",
            name="墙",
            category=ComponentSymbol.Q,
            standard=AtlasStandard.GB_T_50105,
            description="一般墙体",
            typical_dimensions={"width": 200, "height": 3000, "length": 6000},
            drawing_rules=[
                "墙体用双线绘制",
                "墙厚在图中标注",
                "门窗洞口用细实线表示"
            ],
            calculation_rules=[
                "按体积计算",
                "扣除门窗洞口"
            ]
        )
        
        symbols["JQ"] = AtlasSymbolData(
            symbol="JQ",
            name="剪力墙",
            category=ComponentSymbol.JQ,
            standard=AtlasStandard.GB_T_50105,
            description="钢筋混凝土剪力墙",
            typical_dimensions={"width": 200, "height": 3000, "length": 6000},
            drawing_rules=[
                "墙体用粗实线绘制",
                "内部填充表示钢筋混凝土",
                "暗柱、暗梁用虚线表示"
            ],
            calculation_rules=[
                "按体积计算",
                "包含暗柱暗梁体积"
            ]
        )
        
        # 基础类符号
        symbols["DJJ"] = AtlasSymbolData(
            symbol="DJJ",
            name="独立基础",
            category=ComponentSymbol.DJJ,
            standard=AtlasStandard.GB_T_50105,
            description="独立柱基础",
            typical_dimensions={"width": 1500, "height": 800, "length": 1500},
            drawing_rules=[
                "基础轮廓用粗实线绘制",
                "基础顶面标高标注",
                "基础埋深标注"
            ],
            calculation_rules=[
                "按实际体积计算",
                "包含基础梁体积"
            ]
        )
        
        return symbols
    
    def _load_drawing_standards(self) -> Dict[str, Dict[str, Any]]:
        """加载绘图标准"""
        return {
            "line_types": {
                "粗实线": {"width": 0.7, "usage": "可见轮廓线、剖切线"},
                "细实线": {"width": 0.35, "usage": "不可见轮廓线、尺寸线"},
                "细点划线": {"width": 0.35, "usage": "轴线、中心线"},
                "细虚线": {"width": 0.35, "usage": "不可见边线"}
            },
            "text_styles": {
                "标题": {"height": 7, "font": "仿宋"},
                "图名": {"height": 5, "font": "仿宋"},
                "尺寸": {"height": 3.5, "font": "仿宋"},
                "说明": {"height": 3.5, "font": "仿宋"}
            },
            "symbol_sizes": {
                "轴线圆": {"diameter": 8},
                "标高符号": {"height": 3},
                "剖切符号": {"height": 6}
            }
        }
    
    def _load_dimension_patterns(self) -> List[Dict[str, str]]:
        """加载尺寸标注模式"""
        return [
            # 基本尺寸格式
            {"pattern": r"(\d+)", "type": "single", "unit": "mm"},
            {"pattern": r"(\d+)×(\d+)", "type": "section", "unit": "mm"},
            {"pattern": r"(\d+)×(\d+)×(\d+)", "type": "volume", "unit": "mm"},
            
            # 带单位的尺寸
            {"pattern": r"(\d+)mm", "type": "single", "unit": "mm"},
            {"pattern": r"(\d+\.?\d*)m", "type": "single", "unit": "m"},
            
            # 标高格式
            {"pattern": r"[±]?(\d+\.?\d*)", "type": "elevation", "unit": "m"},
            {"pattern": r"EL[\.=]([±]?\d+\.?\d*)", "type": "elevation", "unit": "m"},
            
            # 角度格式
            {"pattern": r"(\d+)°", "type": "angle", "unit": "degree"},
            {"pattern": r"(\d+)°(\d+)'", "type": "angle", "unit": "degree"},
            
            # 比例格式
            {"pattern": r"1:(\d+)", "type": "scale", "unit": "ratio"},
            {"pattern": r"1/(\d+)", "type": "scale", "unit": "ratio"}
        ]
    
    def _load_scale_patterns(self) -> Dict[str, float]:
        """加载图纸比例"""
        return {
            "1:50": 50,
            "1:100": 100,
            "1:150": 150,
            "1:200": 200,
            "1:250": 250,
            "1:300": 300,
            "1:500": 500,
            "1:1000": 1000
        }
    
    def recognize_atlas_symbols(self, image_path: str, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """识别图集符号"""
        results = {
            "recognized_symbols": [],
            "drawing_info": {},
            "dimensions": [],
            "scale_info": {},
            "standards_compliance": {}
        }
        
        try:
            # 从OCR结果中提取文本
            texts = ocr_results.get("processed_texts", [])
            
            # 识别构件符号
            symbols = self._extract_component_symbols(texts)
            results["recognized_symbols"] = symbols
            
            # 识别尺寸标注
            dimensions = self._extract_dimensions(texts)
            results["dimensions"] = dimensions
            
            # 识别图纸比例
            scale_info = self._extract_scale_info(texts)
            results["scale_info"] = scale_info
            
            # 分析绘图规范符合性
            compliance = self._check_standards_compliance(symbols, dimensions)
            results["standards_compliance"] = compliance
            
            # 提取图纸基本信息
            drawing_info = self._extract_drawing_info(texts)
            results["drawing_info"] = drawing_info
            
        except Exception as e:
            logger.error(f"识别图集符号时出错: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def _extract_component_symbols(self, texts: List[str]) -> List[Dict[str, Any]]:
        """提取构件符号"""
        symbols = []
        
        for text in texts:
            # 清理文本
            clean_text = text.strip().upper()
            
            # 匹配构件符号模式
            symbol_patterns = [
                r"(KZ)(\d+)",      # 框架柱
                r"(GZ)(\d+)",      # 构造柱
                r"(KL)(\d+)",      # 框架梁
                r"(LL)(\d+)",      # 连梁
                r"(LB)(\d+)",      # 楼板
                r"(Q)(\d+)",       # 墙
                r"(JQ)(\d+)",      # 剪力墙
                r"(DJJ)(\d+)",     # 独立基础
            ]
            
            for pattern in symbol_patterns:
                matches = re.findall(pattern, clean_text)
                for match in matches:
                    symbol_code = match[0]
                    symbol_number = match[1]
                    
                    if symbol_code in self.atlas_symbols:
                        symbol_data = self.atlas_symbols[symbol_code]
                        symbols.append({
                            "symbol": symbol_code,
                            "number": symbol_number,
                            "full_code": f"{symbol_code}{symbol_number}",
                            "name": symbol_data.name,
                            "category": symbol_data.category.value,
                            "standard": symbol_data.standard.value,
                            "typical_dimensions": symbol_data.typical_dimensions,
                            "source_text": text
                        })
        
        return symbols
    
    def _extract_dimensions(self, texts: List[str]) -> List[Dict[str, Any]]:
        """提取尺寸标注"""
        dimensions = []
        
        for text in texts:
            for pattern_info in self.dimension_patterns:
                pattern = pattern_info["pattern"]
                matches = re.findall(pattern, text)
                
                for match in matches:
                    if isinstance(match, tuple):
                        values = [float(x) for x in match if x.replace('.', '').isdigit()]
                    else:
                        values = [float(match)] if match.replace('.', '').isdigit() else []
                    
                    if values:
                        dimensions.append({
                            "type": pattern_info["type"],
                            "values": values,
                            "unit": pattern_info["unit"],
                            "source_text": text,
                            "pattern": pattern
                        })
        
        return dimensions
    
    def _extract_scale_info(self, texts: List[str]) -> Dict[str, Any]:
        """提取图纸比例信息"""
        scale_info = {
            "detected_scales": [],
            "primary_scale": None,
            "scale_factor": 1.0
        }
        
        for text in texts:
            for scale_text, factor in self.scale_patterns.items():
                if scale_text in text:
                    scale_info["detected_scales"].append({
                        "scale": scale_text,
                        "factor": factor,
                        "source_text": text
                    })
        
        # 确定主要比例
        if scale_info["detected_scales"]:
            # 选择最常见的比例作为主要比例
            primary = scale_info["detected_scales"][0]
            scale_info["primary_scale"] = primary["scale"]
            scale_info["scale_factor"] = primary["factor"]
        
        return scale_info
    
    def _extract_drawing_info(self, texts: List[str]) -> Dict[str, Any]:
        """提取图纸基本信息"""
        drawing_info = {
            "title": "",
            "drawing_number": "",
            "scale": "",
            "date": "",
            "designer": "",
            "checker": ""
        }
        
        # 图纸标题模式
        title_patterns = [
            r"(.+)平面图",
            r"(.+)立面图",
            r"(.+)剖面图",
            r"(.+)详图"
        ]
        
        # 图号模式
        number_patterns = [
            r"图号[：:](.+)",
            r"Drawing No[\.:](.+)",
            r"(\d{2}-\d{2}-\d{2})"
        ]
        
        # 日期模式
        date_patterns = [
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            r"(\d{4}\.\d{1,2}\.\d{1,2})"
        ]
        
        for text in texts:
            # 提取标题
            for pattern in title_patterns:
                match = re.search(pattern, text)
                if match and not drawing_info["title"]:
                    drawing_info["title"] = match.group(1).strip()
            
            # 提取图号
            for pattern in number_patterns:
                match = re.search(pattern, text)
                if match and not drawing_info["drawing_number"]:
                    drawing_info["drawing_number"] = match.group(1).strip()
            
            # 提取日期
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match and not drawing_info["date"]:
                    drawing_info["date"] = match.group(1).strip()
        
        return drawing_info
    
    def _check_standards_compliance(self, symbols: List[Dict], dimensions: List[Dict]) -> Dict[str, Any]:
        """检查标准符合性"""
        compliance = {
            "symbol_compliance": True,
            "dimension_compliance": True,
            "issues": [],
            "recommendations": []
        }
        
        # 检查符号规范性
        for symbol in symbols:
            symbol_code = symbol["symbol"]
            if symbol_code in self.atlas_symbols:
                atlas_data = self.atlas_symbols[symbol_code]
                
                # 检查典型尺寸
                typical_dims = atlas_data.typical_dimensions
                # 这里可以添加更多的符合性检查逻辑
                
        # 检查尺寸标注规范性
        if not dimensions:
            compliance["dimension_compliance"] = False
            compliance["issues"].append("缺少尺寸标注")
            compliance["recommendations"].append("建议添加构件尺寸标注")
        
        return compliance
    
    def generate_atlas_report(self, recognition_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成图集识别报告"""
        report = {
            "summary": {},
            "symbol_analysis": {},
            "dimension_analysis": {},
            "compliance_report": {},
            "recommendations": []
        }
        
        # 汇总信息
        symbols = recognition_results.get("recognized_symbols", [])
        dimensions = recognition_results.get("dimensions", [])
        
        report["summary"] = {
            "total_symbols": len(symbols),
            "total_dimensions": len(dimensions),
            "symbol_types": len(set(s["symbol"] for s in symbols)),
            "primary_scale": recognition_results.get("scale_info", {}).get("primary_scale", "未识别")
        }
        
        # 符号分析
        symbol_stats = {}
        for symbol in symbols:
            symbol_type = symbol["symbol"]
            if symbol_type not in symbol_stats:
                symbol_stats[symbol_type] = {
                    "count": 0,
                    "name": symbol["name"],
                    "numbers": []
                }
            symbol_stats[symbol_type]["count"] += 1
            symbol_stats[symbol_type]["numbers"].append(symbol["number"])
        
        report["symbol_analysis"] = symbol_stats
        
        # 尺寸分析
        dimension_stats = {}
        for dim in dimensions:
            dim_type = dim["type"]
            if dim_type not in dimension_stats:
                dimension_stats[dim_type] = {"count": 0, "values": []}
            dimension_stats[dim_type]["count"] += 1
            dimension_stats[dim_type]["values"].extend(dim["values"])
        
        report["dimension_analysis"] = dimension_stats
        
        # 符合性报告
        report["compliance_report"] = recognition_results.get("standards_compliance", {})
        
        # 建议
        if report["summary"]["total_symbols"] == 0:
            report["recommendations"].append("建议检查图纸清晰度，可能需要提高OCR识别精度")
        
        if report["summary"]["total_dimensions"] == 0:
            report["recommendations"].append("建议添加构件尺寸标注以便准确计算工程量")
        
        return report


# 测试代码
if __name__ == "__main__":
    print("📐 图集规范识别引擎测试")
    print("=" * 50)
    
    # 创建识别引擎
    engine = AtlasRecognitionEngine()
    
    # 模拟OCR结果
    mock_ocr_results = {
        "processed_texts": [
            "KZ1 400×400",
            "KL1 250×500",
            "LB1 厚120",
            "1:100",
            "一层结构平面图",
            "图号：JG-01-01",
            "2024.01.15"
        ]
    }
    
    # 识别图集符号
    results = engine.recognize_atlas_symbols("test_image.jpg", mock_ocr_results)
    
    # 显示识别结果
    print("\n🔍 符号识别结果:")
    for symbol in results["recognized_symbols"]:
        print(f"  {symbol['full_code']} - {symbol['name']}")
    
    print(f"\n📏 尺寸识别结果:")
    for dim in results["dimensions"]:
        print(f"  {dim['type']}: {dim['values']} {dim['unit']}")
    
    print(f"\n📊 图纸信息:")
    drawing_info = results["drawing_info"]
    print(f"  标题: {drawing_info.get('title', '未识别')}")
    print(f"  图号: {drawing_info.get('drawing_number', '未识别')}")
    print(f"  比例: {results['scale_info'].get('primary_scale', '未识别')}")
    
    # 生成报告
    report = engine.generate_atlas_report(results)
    print(f"\n📋 识别报告:")
    print(f"  识别符号: {report['summary']['total_symbols']}个")
    print(f"  识别尺寸: {report['summary']['total_dimensions']}个")
    print(f"  符号类型: {report['summary']['symbol_types']}种")
    
    print("\n✅ 图集识别引擎测试完成！") 