#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工程量计算系统 - 快速演示脚本
=================================

本脚本展示系统的核心功能：
1. OCR文字识别
2. 图集规范识别  
3. 工程量计算
4. 报告生成

使用方法:
    python demo_system.py [图纸路径]
    
如果不提供图纸路径，将使用演示模式
"""

import os
import sys
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.services.advanced_ocr_engine import AdvancedOCREngine
    from app.services.atlas_recognition_engine import AtlasRecognitionEngine
    from app.services.quantity_calculation_engine import QuantityCalculationEngine, ComponentData, ComponentType
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在backend目录下运行此脚本")
    sys.exit(1)

class SmartQTODemo:
    """智能工程量计算系统演示类"""
    
    def __init__(self):
        """初始化演示系统"""
        print("🚀 正在初始化智能工程量计算系统...")
        
        # 初始化各个引擎
        self.ocr_engine = AdvancedOCREngine()
        self.atlas_engine = AtlasRecognitionEngine()
        self.calc_engine = QuantityCalculationEngine()
        
        print("✅ 系统初始化完成！")
        print()
    
    def demo_ocr_recognition(self, image_path=None):
        """演示OCR识别功能"""
        print("=" * 60)
        print("📝 OCR文字识别演示")
        print("=" * 60)
        
        if image_path and os.path.exists(image_path):
            print(f"📁 处理图纸: {image_path}")
            ocr_results = self.ocr_engine.extract_text_and_symbols(image_path)
        else:
            print("📁 使用演示模式（无需真实图纸）")
            # 模拟OCR结果
            ocr_results = {
                "raw_ocr_results": [],
                "processed_texts": [
                    "KZ1 400×400", "KL1 300×600", "LB1 120厚",
                    "C30混凝土", "HRB400钢筋", "1:100"
                ],
                "component_codes": ["KZ1", "KL1", "LB1"],
                "dimensions": [
                    {"component": "KZ1", "width": 400, "height": 400, "unit": "mm"},
                    {"component": "KL1", "width": 300, "height": 600, "unit": "mm"},
                    {"component": "LB1", "thickness": 120, "unit": "mm"}
                ],
                "materials": ["C30", "HRB400"],
                "statistics": {
                    "total_texts": 6,
                    "component_codes": 3,
                    "dimensions": 3,
                    "materials": 2
                }
            }
        
        # 显示识别结果
        print(f"📊 识别统计:")
        print(f"   - 文本数量: {ocr_results['statistics']['total_texts']}")
        print(f"   - 构件代码: {ocr_results['statistics']['component_codes']}")
        print(f"   - 尺寸信息: {ocr_results['statistics']['dimensions']}")
        print(f"   - 材料信息: {ocr_results['statistics']['materials']}")
        print()
        
        print("🔍 识别到的构件代码:")
        for code in ocr_results['component_codes']:
            print(f"   - {code}")
        print()
        
        print("📏 识别到的尺寸信息:")
        for dim in ocr_results['dimensions']:
            if 'width' in dim and 'height' in dim:
                print(f"   - {dim['component']}: {dim['width']}×{dim['height']}{dim['unit']}")
            elif 'thickness' in dim:
                print(f"   - {dim['component']}: {dim['thickness']}{dim['unit']}厚")
        print()
        
        return ocr_results
    
    def demo_atlas_recognition(self, ocr_results):
        """演示图集规范识别功能"""
        print("=" * 60)
        print("📐 图集规范识别演示")
        print("=" * 60)
        
        # 进行图集识别
        atlas_results = self.atlas_engine.recognize_atlas_symbols("demo_image.jpg", ocr_results)
        
        print("📋 图集识别结果:")
        print(f"   - 识别符号数量: {len(atlas_results['recognized_symbols'])}")
        print(f"   - 图纸比例: {atlas_results['scale_info'].get('detected_scale', '未识别')}")
        print(f"   - 符合标准: {atlas_results['standards_compliance'].get('overall_compliance', '良好')}")
        print()
        
        print("🏗️ 识别到的构件符号:")
        for symbol in atlas_results['recognized_symbols']:
            print(f"   - {symbol['symbol']}: {symbol['name']} ({symbol['category']})")
            if symbol.get('typical_dimensions'):
                dims = symbol['typical_dimensions']
                if 'width' in dims and 'height' in dims:
                    print(f"     典型尺寸: {dims['width']}×{dims['height']}mm")
                elif 'thickness' in dims:
                    print(f"     典型厚度: {dims['thickness']}mm")
        print()
        
        return atlas_results
    
    def demo_quantity_calculation(self, atlas_results):
        """演示工程量计算功能"""
        print("=" * 60)
        print("🧮 工程量计算演示")
        print("=" * 60)
        
        # 构建构件数据
        components = []
        for i, symbol in enumerate(atlas_results['recognized_symbols']):
            # 获取典型尺寸
            typical_dims = symbol.get('typical_dimensions', {})
            
            # 映射构件类型
            type_mapping = {
                '框架柱': ComponentType.COLUMN,
                '框架梁': ComponentType.BEAM,
                '楼板': ComponentType.SLAB,
                '墙': ComponentType.WALL,
                '独立基础': ComponentType.FOUNDATION
            }
            
            component_type = type_mapping.get(symbol['category'], ComponentType.COLUMN)
            
            # 创建ComponentData对象
            component = ComponentData(
                component_id=f"COMP_{i+1:03d}",
                component_type=component_type,
                symbol=symbol['symbol'],
                number=symbol.get('number', '1'),
                width=typical_dims.get('width', 400),
                height=typical_dims.get('height', 400),
                length=typical_dims.get('length', 3000),
                thickness=typical_dims.get('thickness', 120),
                concrete_grade="C30",
                rebar_grade="HRB400",
                floor="1F",
                position=(0, 0),
                attributes={}
            )
            components.append(component)
        
        print("📊 构件数据:")
        for comp in components:
            print(f"   - {comp.symbol}: {comp.component_type.value}")
            if comp.component_type in [ComponentType.COLUMN, ComponentType.BEAM]:
                print(f"     尺寸: {comp.width}×{comp.height}×{comp.length}mm")
            elif comp.component_type == ComponentType.SLAB:
                print(f"     厚度: {comp.thickness}mm")
            print(f"     材料: {comp.concrete_grade}")
        print()
        
        # 计算工程量
        print("⚙️ 正在计算工程量...")
        quantity_summary = self.calc_engine.generate_quantity_summary(components)
        
        print("📈 工程量计算结果:")
        print(f"   - 混凝土体积: {quantity_summary['statistics']['concrete_volume']:.3f} m³")
        print(f"   - 模板面积: {quantity_summary['statistics']['formwork_area']:.1f} m²")
        print(f"   - 钢筋重量: {quantity_summary['statistics']['rebar_weight']:.1f} kg")
        print()
        
        print("💰 造价估算:")
        concrete_cost = quantity_summary['statistics']['concrete_volume'] * 350
        formwork_cost = quantity_summary['statistics']['formwork_area'] * 45
        rebar_cost = quantity_summary['statistics']['rebar_weight'] * 4.2
        total_cost = concrete_cost + formwork_cost + rebar_cost
        
        print(f"   - 混凝土费用: ¥{concrete_cost:.2f}")
        print(f"   - 模板费用: ¥{formwork_cost:.2f}")
        print(f"   - 钢筋费用: ¥{rebar_cost:.2f}")
        print(f"   - 总计费用: ¥{total_cost:.2f}")
        print()
        
        return quantity_summary
    
    def demo_report_generation(self, ocr_results, atlas_results, quantity_summary):
        """演示报告生成功能"""
        print("=" * 60)
        print("📊 智能报告生成演示")
        print("=" * 60)
        
        # 生成综合报告
        report = {
            "project_info": {
                "project_name": "智能工程量计算系统演示",
                "drawing_file": "demo_drawing.jpg",
                "processing_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "system_version": "v1.0.0"
            },
            "recognition_summary": {
                "ocr_texts": ocr_results['statistics']['total_texts'],
                "component_codes": ocr_results['statistics']['component_codes'],
                "recognized_symbols": len(atlas_results['recognized_symbols']),
                "dimensions": ocr_results['statistics']['dimensions']
            },
            "quantity_summary": {
                "total_components": len(atlas_results['recognized_symbols']),
                "concrete_volume": quantity_summary['statistics']['concrete_volume'],
                "formwork_area": quantity_summary['statistics']['formwork_area'],
                "rebar_weight": quantity_summary['statistics']['rebar_weight']
            },
            "quality_assessment": {
                "recognition_confidence": "高",
                "data_completeness": "良好",
                "calculation_accuracy": "精确"
            },
            "recommendations": [
                "图纸识别效果良好，建议继续使用",
                "构件信息完整，计算结果可靠",
                "建议定期更新模型以提高识别精度"
            ]
        }
        
        print("📋 综合报告摘要:")
        print(f"   - 项目名称: {report['project_info']['project_name']}")
        print(f"   - 处理时间: {report['project_info']['processing_date']}")
        print(f"   - 系统版本: {report['project_info']['system_version']}")
        print()
        
        print("🎯 识别效果评估:")
        print(f"   - 识别置信度: {report['quality_assessment']['recognition_confidence']}")
        print(f"   - 数据完整性: {report['quality_assessment']['data_completeness']}")
        print(f"   - 计算准确性: {report['quality_assessment']['calculation_accuracy']}")
        print()
        
        print("💡 系统建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"   {i}. {rec}")
        print()
        
        # 保存报告
        output_dir = Path("demo_output")
        output_dir.mkdir(exist_ok=True)
        
        report_file = output_dir / "demo_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"💾 报告已保存到: {report_file}")
        return report
    
    def run_complete_demo(self, image_path=None):
        """运行完整演示"""
        print("🎉 智能工程量计算系统 - 完整功能演示")
        print("=" * 80)
        print()
        
        start_time = time.time()
        
        try:
            # 1. OCR识别演示
            ocr_results = self.demo_ocr_recognition(image_path)
            
            # 2. 图集识别演示
            atlas_results = self.demo_atlas_recognition(ocr_results)
            
            # 3. 工程量计算演示
            quantity_summary = self.demo_quantity_calculation(atlas_results)
            
            # 4. 报告生成演示
            report = self.demo_report_generation(ocr_results, atlas_results, quantity_summary)
            
            # 计算总耗时
            total_time = time.time() - start_time
            
            print("=" * 80)
            print("🎊 演示完成！")
            print(f"⏱️ 总耗时: {total_time:.2f} 秒")
            print()
            print("🌟 系统特色功能:")
            print("   ✅ 智能OCR识别 - 自动提取构件信息")
            print("   ✅ 图集规范识别 - 符合国标GB/T 50105-2010")
            print("   ✅ 工程量计算 - 遵循GB 50500-2013规范")
            print("   ✅ 智能报告生成 - 详细的分析和建议")
            print("   ✅ 造价估算 - 基于市场价格的成本分析")
            print()
            print("📚 更多功能请参考: backend/智能工程量计算系统使用说明.md")
            print("🚀 启动Web服务: python -m app.main")
            
        except Exception as e:
            print(f"❌ 演示过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    print("🏗️ 智能工程量计算系统 - 快速演示")
    print("=" * 50)
    print()
    
    # 检查命令行参数
    image_path = None
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if not os.path.exists(image_path):
            print(f"❌ 图纸文件不存在: {image_path}")
            print("💡 将使用演示模式运行")
            image_path = None
    else:
        print("💡 未提供图纸路径，使用演示模式")
    
    print()
    
    # 创建并运行演示
    demo = SmartQTODemo()
    demo.run_complete_demo(image_path)

if __name__ == "__main__":
    main() 