#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的ChatGPT工程量分析器测试脚本
测试新的提示词和验证逻辑
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.chatgpt_quantity_analyzer import ChatGPTQuantityAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('analyzer_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_improved_analyzer():
    """测试优化后的分析器"""
    
    # 检查API密钥
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("请设置OPENAI_API_KEY环境变量")
        return False
    
    try:
        # 初始化分析器
        logger.info("初始化优化后的ChatGPT分析器...")
        analyzer = ChatGPTQuantityAnalyzer(api_key=api_key)
        
        # 测试文本API
        logger.info("测试文本API连接...")
        if not analyzer.test_text_api_call():
            logger.error("文本API测试失败")
            return False
        
        logger.info("文本API测试成功")
        
        # 查找测试PDF文件
        test_files = []
        for pattern in ['*.pdf', '*.PDF']:
            test_files.extend(project_root.glob(pattern))
        
        if not test_files:
            logger.warning("未找到测试PDF文件，创建模拟测试...")
            return test_mock_analysis(analyzer)
        
        # 测试第一个PDF文件
        test_file = test_files[0]
        logger.info(f"测试PDF文件: {test_file}")
        
        # 项目上下文
        project_context = {
            "project_name": "测试项目",
            "building_type": "住宅建筑",
            "structure_type": "框架结构",
            "design_stage": "施工图设计",
            "special_requirements": "重点关注结构构件"
        }
        
        # 执行分析
        logger.info("开始执行图纸分析...")
        result = analyzer.analyze_drawing_pdf(str(test_file), project_context)
        
        # 输出结果
        logger.info("分析完成，输出结果:")
        print("\n" + "="*80)
        print("优化后的ChatGPT工程量分析结果")
        print("="*80)
        
        # 项目信息
        project_info = result.get('project_info', {})
        print(f"\n📋 项目信息:")
        print(f"  项目名称: {project_info.get('project_name', 'N/A')}")
        print(f"  图纸名称: {project_info.get('drawing_name', 'N/A')}")
        print(f"  图纸编号: {project_info.get('drawing_number', 'N/A')}")
        print(f"  图纸比例: {project_info.get('scale', 'N/A')}")
        print(f"  设计阶段: {project_info.get('design_stage', 'N/A')}")
        
        # 工程量清单
        quantity_list = result.get('quantity_list', [])
        print(f"\n📊 工程量清单 (共{len(quantity_list)}项):")
        
        if quantity_list:
            for i, item in enumerate(quantity_list, 1):
                print(f"\n  {i}. {item.get('component_type', 'N/A')}")
                print(f"     构件编号: {item.get('component_code', 'N/A')}")
                print(f"     截面尺寸: {item.get('section_size', 'N/A')}")
                print(f"     数量: {item.get('component_count', 'N/A')} 个")
                print(f"     工程量: {item.get('quantity', 'N/A')} {item.get('unit', 'N/A')}")
                print(f"     计算公式: {item.get('calculation_formula', 'N/A')}")
                print(f"     备注: {item.get('remarks', 'N/A')}")
        else:
            print("  未识别到工程量项目")
        
        # 汇总信息
        summary = result.get('summary', {})
        print(f"\n📈 分析汇总:")
        print(f"  识别项目数: {summary.get('total_items', 0)}")
        print(f"  分析可信度: {summary.get('analysis_confidence', 0):.2f}")
        print(f"  主体结构体积: {summary.get('main_structure_volume', 0)} m³")
        print(f"  钢筋重量: {summary.get('steel_reinforcement_weight', 0)} t")
        print(f"  模板面积: {summary.get('formwork_area', 0)} m²")
        
        # 缺失信息
        missing_info = summary.get('missing_information', [])
        if missing_info:
            print(f"\n⚠️  缺失信息:")
            for info in missing_info:
                print(f"    - {info}")
        
        # 错误信息
        if 'error' in result:
            print(f"\n❌ 错误信息: {result['error']}")
        
        # 保存详细结果
        output_file = project_root / "improved_analysis_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"详细结果已保存到: {output_file}")
        
        # 质量评估
        print(f"\n🔍 质量评估:")
        confidence = summary.get('analysis_confidence', 0)
        if confidence >= 0.8:
            print("  ✅ 分析质量优秀")
        elif confidence >= 0.6:
            print("  ⚠️  分析质量良好，建议人工复核")
        elif confidence >= 0.4:
            print("  ⚠️  分析质量一般，需要人工核实")
        else:
            print("  ❌ 分析质量较差，建议重新分析或人工处理")
        
        print("\n" + "="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_analysis(analyzer):
    """模拟分析测试（当没有PDF文件时）"""
    logger.info("执行模拟分析测试...")
    
    # 创建模拟结果
    mock_result = {
        "project_info": {
            "project_name": "测试项目",
            "drawing_name": "一层平面图",
            "drawing_number": "A-01",
            "scale": "1:100",
            "design_stage": "施工图"
        },
        "quantity_list": [
            {
                "sequence": 1,
                "component_type": "框架柱",
                "component_code": "KZ-1",
                "component_count": 12,
                "section_size": "500×500",
                "project_name": "现浇混凝土柱",
                "unit": "m³",
                "quantity": 18.0,
                "calculation_formula": "0.5×0.5×3.0×12",
                "remarks": "一层框架柱，层高3.0m"
            }
        ],
        "summary": {
            "total_items": 1,
            "main_structure_volume": 18.0,
            "steel_reinforcement_weight": 0,
            "formwork_area": 0,
            "analysis_confidence": 0.85,
            "missing_information": []
        }
    }
    
    # 测试验证逻辑
    validated_result = analyzer._validate_and_fix_result(mock_result)
    
    print("\n模拟分析测试结果:")
    print(json.dumps(validated_result, ensure_ascii=False, indent=2))
    
    return True

if __name__ == "__main__":
    print("优化后的ChatGPT工程量分析器测试")
    print("="*50)
    
    success = test_improved_analyzer()
    
    if success:
        print("\n✅ 测试完成")
    else:
        print("\n❌ 测试失败")
        sys.exit(1) 