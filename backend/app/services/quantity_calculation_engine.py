#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工程量计算规范引擎 - GB 50500-2013
实现建设工程工程量清单计价规范的计算规则
"""

import json
import math
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# 配置日志
logger = logging.getLogger(__name__)

class ComponentType(Enum):
    """构件类型枚举"""
    COLUMN = "column"       # 柱
    BEAM = "beam"          # 梁
    SLAB = "slab"          # 板
    WALL = "wall"          # 墙
    FOUNDATION = "foundation"  # 基础
    STAIR = "stair"        # 楼梯

class CalculationUnit(Enum):
    """计算单位枚举"""
    M3 = "m³"              # 立方米（混凝土）
    M2 = "m²"              # 平方米（模板、装饰）
    M = "m"                # 米（长度）
    KG = "kg"              # 千克（钢筋）
    T = "t"                # 吨（钢材）

@dataclass
class ComponentData:
    """构件数据结构"""
    component_id: str
    component_type: ComponentType
    symbol: str            # 构件符号 KZ, KL等
    number: str           # 构件编号
    
    # 几何尺寸 (mm)
    width: float = 0
    height: float = 0
    length: float = 0
    thickness: float = 0
    
    # 材料信息
    concrete_grade: str = "C30"
    rebar_grade: str = "HRB400"
    
    # 位置信息
    floor: str = "1F"
    position: Tuple[float, float] = (0, 0)
    
    # 其他属性
    attributes: Dict[str, Any] = None

class QuantityCalculationEngine:
    """工程量计算规范引擎"""
    
    def __init__(self):
        """初始化计算引擎"""
        self.gb50500_rules = self._load_gb50500_rules()
        self.deduction_rules = self._load_deduction_rules()
        self.standard_sections = self._load_standard_sections()
        
    def _load_gb50500_rules(self) -> Dict[str, Dict[str, Any]]:
        """加载GB 50500-2013计算规则"""
        return {
            # 010101001 - 现浇混凝土柱
            "010101001": {
                "name": "现浇混凝土柱",
                "unit": CalculationUnit.M3,
                "calculation_method": "column_concrete",
                "description": "按设计图示尺寸以体积计算，不扣除构件内钢筋、预埋铁件所占体积",
                "deduction_rules": ["beam_intersection"]
            },
            
            # 010101002 - 现浇混凝土梁
            "010101002": {
                "name": "现浇混凝土梁",
                "unit": CalculationUnit.M3,
                "calculation_method": "beam_concrete",
                "description": "按设计图示尺寸以体积计算，不扣除构件内钢筋、预埋铁件所占体积",
                "deduction_rules": []
            },
            
            # 010101003 - 现浇混凝土板
            "010101003": {
                "name": "现浇混凝土板",
                "unit": CalculationUnit.M3,
                "calculation_method": "slab_concrete",
                "description": "按设计图示尺寸以体积计算，不扣除构件内钢筋、预埋铁件所占体积",
                "deduction_rules": ["opening_deduction"]
            },
            
            # 010101004 - 现浇混凝土墙
            "010101004": {
                "name": "现浇混凝土墙",
                "unit": CalculationUnit.M3,
                "calculation_method": "wall_concrete",
                "description": "按设计图示尺寸以体积计算",
                "deduction_rules": ["door_window_deduction"]
            },
            
            # 010101005 - 现浇混凝土基础
            "010101005": {
                "name": "现浇混凝土基础",
                "unit": CalculationUnit.M3,
                "calculation_method": "foundation_concrete",
                "description": "按设计图示尺寸以体积计算",
                "deduction_rules": []
            },
            
            # 010102001 - 现浇混凝土柱模板
            "010102001": {
                "name": "现浇混凝土柱模板",
                "unit": CalculationUnit.M2,
                "calculation_method": "column_formwork",
                "description": "按设计图示混凝土与模板的接触面积计算",
                "deduction_rules": []
            },
            
            # 010102002 - 现浇混凝土梁模板
            "010102002": {
                "name": "现浇混凝土梁模板",
                "unit": CalculationUnit.M2,
                "calculation_method": "beam_formwork",
                "description": "按设计图示混凝土与模板的接触面积计算",
                "deduction_rules": []
            },
            
            # 010102003 - 现浇混凝土板模板
            "010102003": {
                "name": "现浇混凝土板模板",
                "unit": CalculationUnit.M2,
                "calculation_method": "slab_formwork",
                "description": "按设计图示混凝土与模板的接触面积计算",
                "deduction_rules": ["opening_deduction"]
            },
            
            # 010401001 - 钢筋
            "010401001": {
                "name": "钢筋",
                "unit": CalculationUnit.KG,
                "calculation_method": "reinforcement_weight",
                "description": "按设计图示钢筋长度乘以单位重量计算",
                "deduction_rules": []
            }
        }
    
    def _load_deduction_rules(self) -> Dict[str, Dict[str, Any]]:
        """加载扣减规则"""
        return {
            "beam_intersection": {
                "description": "梁柱节点重复计算扣减",
                "applicable_to": ["column"],
                "method": "calculate_beam_intersection_volume"
            },
            "opening_deduction": {
                "description": "洞口面积扣减",
                "applicable_to": ["slab", "wall"],
                "method": "calculate_opening_deduction",
                "min_opening_area": 0.3  # 单个洞口面积>0.3m²才扣减
            },
            "door_window_deduction": {
                "description": "门窗洞口扣减",
                "applicable_to": ["wall"],
                "method": "calculate_door_window_deduction"
            }
        }
    
    def _load_standard_sections(self) -> Dict[str, Dict[str, float]]:
        """加载标准构件截面"""
        return {
            # 标准柱截面
            "KZ1": {"width": 400, "height": 400},
            "KZ2": {"width": 500, "height": 500},
            "KZ3": {"width": 600, "height": 600},
            
            # 标准梁截面
            "KL1": {"width": 250, "height": 500},
            "KL2": {"width": 300, "height": 600},
            "KL3": {"width": 350, "height": 700},
            
            # 标准板厚度
            "LB1": {"thickness": 100},
            "LB2": {"thickness": 120},
            "LB3": {"thickness": 150},
        }
    
    def calculate_component_quantities(self, component: ComponentData) -> Dict[str, Any]:
        """计算单个构件的工程量"""
        results = {}
        
        try:
            # 根据构件类型选择计算方法
            if component.component_type == ComponentType.COLUMN:
                results.update(self._calculate_column_quantities(component))
            elif component.component_type == ComponentType.BEAM:
                results.update(self._calculate_beam_quantities(component))
            elif component.component_type == ComponentType.SLAB:
                results.update(self._calculate_slab_quantities(component))
            elif component.component_type == ComponentType.WALL:
                results.update(self._calculate_wall_quantities(component))
            elif component.component_type == ComponentType.FOUNDATION:
                results.update(self._calculate_foundation_quantities(component))
            
            # 添加构件基本信息
            results["component_info"] = {
                "id": component.component_id,
                "type": component.component_type.value,
                "symbol": component.symbol,
                "number": component.number,
                "dimensions": {
                    "width": component.width,
                    "height": component.height,
                    "length": component.length,
                    "thickness": component.thickness
                }
            }
            
        except Exception as e:
            logger.error(f"计算构件{component.component_id}工程量时出错: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def _calculate_column_quantities(self, component: ComponentData) -> Dict[str, float]:
        """计算柱的工程量"""
        results = {}
        
        # 转换单位 mm -> m
        width_m = component.width / 1000
        height_m = component.height / 1000
        length_m = component.length / 1000  # 柱高
        
        # 混凝土工程量 (010101001)
        section_area = width_m * height_m
        concrete_volume = section_area * length_m
        
        # 扣减梁柱节点重复计算部分
        beam_deduction = self._calculate_beam_intersection_volume(component)
        concrete_volume = max(0, concrete_volume - beam_deduction)
        
        results["010101001"] = round(concrete_volume, 3)
        
        # 模板工程量 (010102001)
        perimeter = 2 * (width_m + height_m)
        formwork_area = perimeter * length_m
        results["010102001"] = round(formwork_area, 2)
        
        # 钢筋工程量 (010401001) - 估算
        rebar_weight = self._estimate_column_rebar(component, concrete_volume)
        results["010401001"] = round(rebar_weight, 1)
        
        return results
    
    def _calculate_beam_quantities(self, component: ComponentData) -> Dict[str, float]:
        """计算梁的工程量"""
        results = {}
        
        # 转换单位 mm -> m
        width_m = component.width / 1000
        height_m = component.height / 1000
        length_m = component.length / 1000
        
        # 混凝土工程量 (010101002)
        section_area = width_m * height_m
        concrete_volume = section_area * length_m
        results["010101002"] = round(concrete_volume, 3)
        
        # 模板工程量 (010102002)
        # 梁模板 = 底模 + 两侧模
        bottom_area = width_m * length_m
        side_area = 2 * height_m * length_m
        formwork_area = bottom_area + side_area
        results["010102002"] = round(formwork_area, 2)
        
        # 钢筋工程量 (010401001) - 估算
        rebar_weight = self._estimate_beam_rebar(component, concrete_volume)
        results["010401001"] = round(rebar_weight, 1)
        
        return results
    
    def _calculate_slab_quantities(self, component: ComponentData) -> Dict[str, float]:
        """计算板的工程量"""
        results = {}
        
        # 转换单位 mm -> m
        width_m = component.width / 1000
        length_m = component.length / 1000
        thickness_m = component.thickness / 1000
        
        # 板面积
        slab_area = width_m * length_m
        
        # 扣减洞口面积
        opening_deduction = self._calculate_opening_deduction(component)
        net_area = max(0, slab_area - opening_deduction)
        
        # 混凝土工程量 (010101003)
        concrete_volume = net_area * thickness_m
        results["010101003"] = round(concrete_volume, 3)
        
        # 模板工程量 (010102003) - 只计算底模
        formwork_area = net_area
        results["010102003"] = round(formwork_area, 2)
        
        # 钢筋工程量 (010401001) - 估算
        rebar_weight = self._estimate_slab_rebar(component, concrete_volume)
        results["010401001"] = round(rebar_weight, 1)
        
        return results
    
    def _calculate_wall_quantities(self, component: ComponentData) -> Dict[str, float]:
        """计算墙的工程量"""
        results = {}
        
        # 转换单位 mm -> m
        width_m = component.width / 1000  # 墙厚
        height_m = component.height / 1000  # 墙高
        length_m = component.length / 1000  # 墙长
        
        # 墙体积
        wall_volume = width_m * height_m * length_m
        
        # 扣减门窗洞口
        door_window_deduction = self._calculate_door_window_deduction(component)
        net_volume = max(0, wall_volume - door_window_deduction)
        
        # 混凝土工程量 (010101004)
        results["010101004"] = round(net_volume, 3)
        
        # 模板工程量 - 双面模板
        wall_area = height_m * length_m
        formwork_area = 2 * wall_area  # 双面
        results["010102004"] = round(formwork_area, 2)
        
        return results
    
    def _calculate_foundation_quantities(self, component: ComponentData) -> Dict[str, float]:
        """计算基础的工程量"""
        results = {}
        
        # 转换单位 mm -> m
        width_m = component.width / 1000
        height_m = component.height / 1000
        length_m = component.length / 1000
        
        # 基础体积
        foundation_volume = width_m * height_m * length_m
        
        # 混凝土工程量 (010101005)
        results["010101005"] = round(foundation_volume, 3)
        
        # 基础一般不计算模板（土模）
        
        return results
    
    def _calculate_beam_intersection_volume(self, column: ComponentData) -> float:
        """计算梁柱节点重复体积"""
        # 简化计算：假设柱子与4根梁相交
        # 实际应根据图纸分析具体相交的梁
        
        # 转换单位
        col_width = column.width / 1000
        col_height = column.height / 1000
        
        # 假设标准梁高度600mm
        beam_height = 0.6
        
        # 重复体积 = 柱截面积 × 梁高度
        intersection_volume = col_width * col_height * beam_height
        
        return intersection_volume
    
    def _calculate_opening_deduction(self, component: ComponentData) -> float:
        """计算洞口扣减面积"""
        # 这里应该从图纸识别结果中获取洞口信息
        # 简化处理：根据构件大小估算
        
        total_area = (component.width * component.length) / 1000000  # 转换为m²
        
        # 如果面积大于50m²，假设有洞口
        if total_area > 50:
            # 假设洞口面积为总面积的5%
            opening_area = total_area * 0.05
            # 只有单个洞口>0.3m²才扣减
            if opening_area > 0.3:
                return opening_area
        
        return 0
    
    def _calculate_door_window_deduction(self, component: ComponentData) -> float:
        """计算门窗洞口扣减体积"""
        # 简化处理：根据墙体长度估算门窗数量
        wall_length = component.length / 1000
        
        # 假设每6米有一个门窗洞口
        opening_count = max(1, int(wall_length / 6))
        
        # 标准门窗洞口体积 (1.5m×2.1m×墙厚)
        wall_thickness = component.width / 1000
        opening_volume = opening_count * 1.5 * 2.1 * wall_thickness
        
        return opening_volume
    
    def _estimate_column_rebar(self, component: ComponentData, concrete_volume: float) -> float:
        """估算柱钢筋重量"""
        # 按经验公式：柱钢筋用量约为80-120kg/m³混凝土
        rebar_ratio = 100  # kg/m³
        return concrete_volume * rebar_ratio
    
    def _estimate_beam_rebar(self, component: ComponentData, concrete_volume: float) -> float:
        """估算梁钢筋重量"""
        # 按经验公式：梁钢筋用量约为110-150kg/m³混凝土
        rebar_ratio = 130  # kg/m³
        return concrete_volume * rebar_ratio
    
    def _estimate_slab_rebar(self, component: ComponentData, concrete_volume: float) -> float:
        """估算板钢筋重量"""
        # 按经验公式：板钢筋用量约为60-80kg/m³混凝土
        rebar_ratio = 70  # kg/m³
        return concrete_volume * rebar_ratio
    
    def generate_quantity_summary(self, components: List[ComponentData]) -> Dict[str, Any]:
        """生成工程量汇总表"""
        summary = {}
        
        # 初始化汇总结构
        for rule_code, rule_info in self.gb50500_rules.items():
            summary[rule_code] = {
                "name": rule_info["name"],
                "unit": rule_info["unit"].value,
                "quantity": 0.0,
                "components": []
            }
        
        # 计算各构件工程量并汇总
        for component in components:
            try:
                quantities = self.calculate_component_quantities(component)
                
                # 汇总到对应的清单项
                for rule_code, quantity in quantities.items():
                    if rule_code in summary and isinstance(quantity, (int, float)):
                        summary[rule_code]["quantity"] += quantity
                        summary[rule_code]["components"].append({
                            "id": component.component_id,
                            "type": component.component_type.value,
                            "symbol": component.symbol,
                            "quantity": quantity
                        })
                        
            except Exception as e:
                logger.error(f"汇总构件{component.component_id}时出错: {str(e)}")
        
        # 清理空项目
        summary = {k: v for k, v in summary.items() if v["quantity"] > 0}
        
        # 添加统计信息
        summary["statistics"] = {
            "total_components": len(components),
            "total_items": len(summary) - 1,  # 减去statistics本身
            "concrete_volume": sum(v["quantity"] for k, v in summary.items() 
                                 if k.startswith("010101") and k != "statistics"),
            "formwork_area": sum(v["quantity"] for k, v in summary.items() 
                               if k.startswith("010102") and k != "statistics"),
            "rebar_weight": summary.get("010401001", {}).get("quantity", 0)
        }
        
        return summary
    
    def export_quantity_list(self, summary: Dict[str, Any], output_path: str = "工程量清单.json"):
        """导出工程量清单"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"📊 工程量清单已导出到: {output_path}")
        except Exception as e:
            logger.error(f"导出工程量清单失败: {str(e)}")


# 测试代码
if __name__ == "__main__":
    print("🧮 工程量计算规范引擎测试")
    print("=" * 50)
    
    # 创建计算引擎
    engine = QuantityCalculationEngine()
    
    # 创建测试构件
    test_components = [
        ComponentData(
            component_id="KZ1-001",
            component_type=ComponentType.COLUMN,
            symbol="KZ",
            number="1",
            width=400,
            height=400,
            length=3000,  # 柱高3m
        ),
        ComponentData(
            component_id="KL1-001",
            component_type=ComponentType.BEAM,
            symbol="KL",
            number="1",
            width=250,
            height=500,
            length=6000,  # 梁长6m
        ),
        ComponentData(
            component_id="LB1-001",
            component_type=ComponentType.SLAB,
            symbol="LB",
            number="1",
            width=6000,
            length=8000,
            thickness=120,  # 板厚120mm
        )
    ]
    
    # 生成工程量汇总
    summary = engine.generate_quantity_summary(test_components)
    
    # 显示结果
    print("\n📊 工程量汇总结果:")
    for code, item in summary.items():
        if code != "statistics":
            print(f"  {code} - {item['name']}: {item['quantity']} {item['unit']}")
    
    # 显示统计信息
    stats = summary.get("statistics", {})
    print(f"\n📈 统计信息:")
    print(f"  构件总数: {stats.get('total_components', 0)}个")
    print(f"  清单项目: {stats.get('total_items', 0)}项")
    print(f"  混凝土: {stats.get('concrete_volume', 0):.2f} m³")
    print(f"  模板: {stats.get('formwork_area', 0):.2f} m²")
    print(f"  钢筋: {stats.get('rebar_weight', 0):.1f} kg")
    
    print("\n✅ 工程量计算引擎测试完成！") 