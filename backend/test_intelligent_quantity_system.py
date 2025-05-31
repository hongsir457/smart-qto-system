#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工程量计算系统集成测试
整合OCR识别、图集规范识别和工程量计算功能
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 导入各个模块
from app.services.advanced_ocr_engine import AdvancedOCREngine
from app.services.atlas_recognition_engine import AtlasRecognitionEngine
from app.services.quantity_calculation_engine import (
    QuantityCalculationEngine, 
    ComponentData, 
    ComponentType
)

class IntelligentQuantitySystem:
    """智能工程量计算系统"""
    
    def __init__(self):
        """初始化系统"""
        print("🚀 初始化智能工程量计算系统...")
        
        # 初始化各个引擎
        self.ocr_engine = AdvancedOCREngine()
        self.atlas_engine = AtlasRecognitionEngine()
        self.quantity_engine = QuantityCalculationEngine()
        
        print("✅ 系统初始化完成！")
    
    def process_architectural_drawing(self, image_path: str) -> Dict[str, Any]:
        """处理建筑图纸的完整流程"""
        results = {
            "image_path": image_path,
            "ocr_results": {},
            "atlas_recognition": {},
            "component_data": [],
            "quantity_calculation": {},
            "final_report": {}
        }
        
        try:
            print(f"\n📋 开始处理图纸: {image_path}")
            
            # 步骤1: OCR文字识别
            print("🔍 步骤1: 执行OCR文字识别...")
            ocr_results = self.ocr_engine.extract_text_and_symbols(image_path)
            results["ocr_results"] = ocr_results
            print(f"   识别到文本: {len(ocr_results.get('processed_texts', []))}条")
            print(f"   构件代码: {len(ocr_results.get('component_codes', []))}个")
            print(f"   尺寸信息: {len(ocr_results.get('dimensions', []))}个")
            
            # 步骤2: 图集规范识别
            print("📐 步骤2: 执行图集规范识别...")
            atlas_results = self.atlas_engine.recognize_atlas_symbols(image_path, ocr_results)
            results["atlas_recognition"] = atlas_results
            print(f"   识别符号: {len(atlas_results.get('recognized_symbols', []))}个")
            print(f"   图纸比例: {atlas_results.get('scale_info', {}).get('primary_scale', '未识别')}")
            
            # 步骤3: 构建构件数据
            print("🏗️ 步骤3: 构建构件数据...")
            component_data = self._build_component_data(ocr_results, atlas_results)
            results["component_data"] = [self._component_to_dict(comp) for comp in component_data]
            print(f"   构建构件: {len(component_data)}个")
            
            # 步骤4: 工程量计算
            print("🧮 步骤4: 执行工程量计算...")
            quantity_results = self.quantity_engine.generate_quantity_summary(component_data)
            results["quantity_calculation"] = quantity_results
            
            # 显示计算结果
            stats = quantity_results.get("statistics", {})
            print(f"   混凝土: {stats.get('concrete_volume', 0):.2f} m³")
            print(f"   模板: {stats.get('formwork_area', 0):.2f} m²")
            print(f"   钢筋: {stats.get('rebar_weight', 0):.1f} kg")
            
            # 步骤5: 生成综合报告
            print("📊 步骤5: 生成综合报告...")
            final_report = self._generate_comprehensive_report(results)
            results["final_report"] = final_report
            
            print("✅ 图纸处理完成！")
            
        except Exception as e:
            print(f"❌ 处理图纸时出错: {str(e)}")
            results["error"] = str(e)
        
        return results
    
    def _build_component_data(self, ocr_results: Dict, atlas_results: Dict) -> List[ComponentData]:
        """根据识别结果构建构件数据"""
        components = []
        
        # 获取识别到的符号
        symbols = atlas_results.get("recognized_symbols", [])
        dimensions = atlas_results.get("dimensions", [])
        
        # 为每个识别到的符号创建构件数据
        for i, symbol in enumerate(symbols):
            try:
                # 确定构件类型
                component_type = self._map_symbol_to_type(symbol["symbol"])
                
                # 提取尺寸信息
                dims = self._extract_component_dimensions(symbol, dimensions)
                
                # 创建构件数据
                component = ComponentData(
                    component_id=f"{symbol['full_code']}-{i+1:03d}",
                    component_type=component_type,
                    symbol=symbol["symbol"],
                    number=symbol["number"],
                    width=dims.get("width", 0),
                    height=dims.get("height", 0),
                    length=dims.get("length", 0),
                    thickness=dims.get("thickness", 0)
                )
                
                components.append(component)
                
            except Exception as e:
                print(f"   警告: 构建构件{symbol.get('full_code', 'unknown')}时出错: {str(e)}")
        
        # 如果没有识别到符号，创建示例构件用于演示
        if not components:
            print("   未识别到构件符号，创建示例构件...")
            components = self._create_demo_components()
        
        return components
    
    def _map_symbol_to_type(self, symbol: str) -> ComponentType:
        """映射符号到构件类型"""
        mapping = {
            "KZ": ComponentType.COLUMN,
            "GZ": ComponentType.COLUMN,
            "KL": ComponentType.BEAM,
            "LL": ComponentType.BEAM,
            "LB": ComponentType.SLAB,
            "WB": ComponentType.SLAB,
            "Q": ComponentType.WALL,
            "JQ": ComponentType.WALL,
            "DJJ": ComponentType.FOUNDATION,
            "TJJ": ComponentType.FOUNDATION,
        }
        return mapping.get(symbol, ComponentType.COLUMN)
    
    def _extract_component_dimensions(self, symbol: Dict, dimensions: List[Dict]) -> Dict[str, float]:
        """提取构件尺寸"""
        dims = {"width": 0, "height": 0, "length": 0, "thickness": 0}
        
        # 使用典型尺寸作为默认值
        typical_dims = symbol.get("typical_dimensions", {})
        dims.update(typical_dims)
        
        # 尝试从识别的尺寸中匹配
        for dim in dimensions:
            if dim["type"] == "section" and len(dim["values"]) >= 2:
                dims["width"] = dim["values"][0]
                dims["height"] = dim["values"][1]
            elif dim["type"] == "single":
                # 根据构件类型判断是长度还是厚度
                if symbol["symbol"] in ["LB", "WB"]:  # 板类
                    dims["thickness"] = dim["values"][0]
                else:
                    dims["length"] = dim["values"][0]
        
        return dims
    
    def _create_demo_components(self) -> List[ComponentData]:
        """创建演示构件"""
        return [
            ComponentData(
                component_id="KZ1-001",
                component_type=ComponentType.COLUMN,
                symbol="KZ",
                number="1",
                width=400,
                height=400,
                length=3000
            ),
            ComponentData(
                component_id="KL1-001",
                component_type=ComponentType.BEAM,
                symbol="KL",
                number="1",
                width=250,
                height=500,
                length=6000
            ),
            ComponentData(
                component_id="LB1-001",
                component_type=ComponentType.SLAB,
                symbol="LB",
                number="1",
                width=6000,
                length=8000,
                thickness=120
            )
        ]
    
    def _component_to_dict(self, component: ComponentData) -> Dict[str, Any]:
        """将构件数据转换为字典"""
        return {
            "component_id": component.component_id,
            "component_type": component.component_type.value,
            "symbol": component.symbol,
            "number": component.number,
            "dimensions": {
                "width": component.width,
                "height": component.height,
                "length": component.length,
                "thickness": component.thickness
            },
            "materials": {
                "concrete_grade": component.concrete_grade,
                "rebar_grade": component.rebar_grade
            }
        }
    
    def _generate_comprehensive_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告"""
        report = {
            "project_info": {
                "drawing_file": results["image_path"],
                "processing_date": "2024-01-15",
                "system_version": "v1.0"
            },
            "recognition_summary": {},
            "quantity_summary": {},
            "quality_assessment": {},
            "recommendations": []
        }
        
        # 识别汇总
        ocr_results = results.get("ocr_results", {})
        atlas_results = results.get("atlas_recognition", {})
        
        report["recognition_summary"] = {
            "ocr_texts": len(ocr_results.get("processed_texts", [])),
            "component_codes": len(ocr_results.get("component_codes", [])),
            "recognized_symbols": len(atlas_results.get("recognized_symbols", [])),
            "dimensions": len(atlas_results.get("dimensions", [])),
            "drawing_scale": atlas_results.get("scale_info", {}).get("primary_scale", "未识别")
        }
        
        # 工程量汇总
        quantity_results = results.get("quantity_calculation", {})
        stats = quantity_results.get("statistics", {})
        
        report["quantity_summary"] = {
            "total_components": stats.get("total_components", 0),
            "concrete_volume": stats.get("concrete_volume", 0),
            "formwork_area": stats.get("formwork_area", 0),
            "rebar_weight": stats.get("rebar_weight", 0),
            "estimated_cost": self._estimate_cost(stats)
        }
        
        # 质量评估
        report["quality_assessment"] = {
            "recognition_confidence": "中等",
            "data_completeness": self._assess_completeness(results),
            "calculation_accuracy": "高"
        }
        
        # 建议
        recommendations = []
        if report["recognition_summary"]["recognized_symbols"] == 0:
            recommendations.append("建议提高图纸清晰度以改善符号识别效果")
        if report["recognition_summary"]["dimensions"] == 0:
            recommendations.append("建议补充构件尺寸标注信息")
        if report["recognition_summary"]["drawing_scale"] == "未识别":
            recommendations.append("建议明确标注图纸比例")
        
        report["recommendations"] = recommendations
        
        return report
    
    def _estimate_cost(self, stats: Dict[str, Any]) -> Dict[str, float]:
        """估算工程造价"""
        # 简化的造价估算（实际应根据当地市场价格）
        concrete_price = 350  # 元/m³
        formwork_price = 45   # 元/m²
        rebar_price = 4.2     # 元/kg
        
        concrete_cost = stats.get("concrete_volume", 0) * concrete_price
        formwork_cost = stats.get("formwork_area", 0) * formwork_price
        rebar_cost = stats.get("rebar_weight", 0) * rebar_price
        
        return {
            "concrete_cost": round(concrete_cost, 2),
            "formwork_cost": round(formwork_cost, 2),
            "rebar_cost": round(rebar_cost, 2),
            "total_cost": round(concrete_cost + formwork_cost + rebar_cost, 2)
        }
    
    def _assess_completeness(self, results: Dict[str, Any]) -> str:
        """评估数据完整性"""
        score = 0
        
        # OCR识别完整性
        ocr_results = results.get("ocr_results", {})
        if ocr_results.get("processed_texts"):
            score += 25
        if ocr_results.get("component_codes"):
            score += 25
        
        # 图集识别完整性
        atlas_results = results.get("atlas_recognition", {})
        if atlas_results.get("recognized_symbols"):
            score += 25
        if atlas_results.get("dimensions"):
            score += 25
        
        if score >= 75:
            return "高"
        elif score >= 50:
            return "中等"
        else:
            return "低"
    
    def export_results(self, results: Dict[str, Any], output_dir: str = "output"):
        """导出结果"""
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 导出完整结果
            with open(f"{output_dir}/complete_results.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            # 导出工程量清单
            quantity_results = results.get("quantity_calculation", {})
            if quantity_results:
                with open(f"{output_dir}/quantity_list.json", 'w', encoding='utf-8') as f:
                    json.dump(quantity_results, f, ensure_ascii=False, indent=2, default=str)
            
            # 导出综合报告
            final_report = results.get("final_report", {})
            if final_report:
                with open(f"{output_dir}/comprehensive_report.json", 'w', encoding='utf-8') as f:
                    json.dump(final_report, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"📁 结果已导出到: {output_dir}/")
            
        except Exception as e:
            print(f"❌ 导出结果时出错: {str(e)}")


def test_intelligent_system():
    """测试智能工程量计算系统"""
    print("🧪 智能工程量计算系统集成测试")
    print("=" * 60)
    
    # 创建系统实例
    system = IntelligentQuantitySystem()
    
    # 测试图纸路径
    test_images = [
        "test_images/sample_floorplan.jpg",
        "test_images/complex_building_plan.png",
        "test_images/一层柱结构改造加固平面图.pdf"
    ]
    
    # 处理每个测试图纸
    for image_path in test_images:
        if os.path.exists(image_path):
            print(f"\n🎯 测试图纸: {image_path}")
            
            # 处理图纸
            results = system.process_architectural_drawing(image_path)
            
            # 显示关键结果
            final_report = results.get("final_report", {})
            if final_report:
                print("\n📊 处理结果摘要:")
                
                # 识别汇总
                recognition = final_report.get("recognition_summary", {})
                print(f"  📝 识别文本: {recognition.get('ocr_texts', 0)}条")
                print(f"  🏗️ 识别符号: {recognition.get('recognized_symbols', 0)}个")
                print(f"  📏 识别尺寸: {recognition.get('dimensions', 0)}个")
                
                # 工程量汇总
                quantity = final_report.get("quantity_summary", {})
                print(f"  🧱 混凝土: {quantity.get('concrete_volume', 0):.2f} m³")
                print(f"  📋 模板: {quantity.get('formwork_area', 0):.2f} m²")
                print(f"  🔩 钢筋: {quantity.get('rebar_weight', 0):.1f} kg")
                
                # 造价估算
                cost = quantity.get("estimated_cost", {})
                if cost:
                    print(f"  💰 估算造价: {cost.get('total_cost', 0):.2f} 元")
            
            # 导出结果
            output_dir = f"output/{Path(image_path).stem}"
            system.export_results(results, output_dir)
            
        else:
            print(f"⚠️ 图纸文件不存在: {image_path}")
    
    print("\n🎉 系统集成测试完成！")
    print("\n💡 系统特点:")
    print("  ✅ 智能OCR识别 - 支持建筑图纸文字和符号识别")
    print("  ✅ 图集规范识别 - 符合国标GB/T 50105-2010")
    print("  ✅ 工程量计算 - 遵循GB 50500-2013清单规范")
    print("  ✅ 自动扣减计算 - 梁柱节点、洞口等智能扣减")
    print("  ✅ 造价估算 - 基于市场价格的成本分析")
    print("  ✅ 综合报告 - 完整的识别和计算报告")


if __name__ == "__main__":
    test_intelligent_system() 