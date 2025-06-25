#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双轨协同分析完整演示
展示 OCR + Vision 协同工作流程
"""

import os
import sys
import json
import logging
import time
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "app"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demonstrate_dual_track_architecture():
    """演示双轨协同分析架构"""
    
    print("🔄 双轨协同分析架构演示")
    print("="*80)
    
    # 展示架构图
    print("\n📊 双轨协同分析架构图:")
    print("""
    ┌─────────────────┐
    │   原始图纸     │
    └─────────────────┘
              │
              ▼
    ┌─────────────────┐
    │   网格切片     │
    │  (记录坐标)     │
    └─────────────────┘
              │
         ┌────▼────┐
         │ 每个切片 │
         └────┬────┘
              │
    ┌─────────▼─────────┐
    │   PaddleOCR      │
    │  文本提取+位置    │
    └─────────┬─────────┘
              │
    ┌─────────▼─────────┐
    │   智能分类器      │
    │ 编号/尺寸/材料/轴线│
    └─────────┬─────────┘
              │
    ┌─────────▼─────────┐
    │  增强提示生成     │
    │ OCR引导Vision     │
    └─────────┬─────────┘
              │
    ┌─────────▼─────────┐
    │   GPT Vision     │
    │  语义理解+验证    │
    └─────────┬─────────┘
              │
    ┌─────────▼─────────┐
    │   结果融合       │
    │  互补+去重+验证   │
    └─────────┬─────────┘
              │
    ┌─────────▼─────────┐
    │  坐标还原+可视化  │
    │   最终构件清单    │
    └───────────────────┘
    """)
    
    # 展示核心优势
    print("\n🎯 双轨协同核心优势:")
    advantages = [
        "1. 精准定位: OCR准确提取文字位置，Vision验证语义",
        "2. 互补增强: OCR处理文字，Vision理解图像，相得益彰",
        "3. 引导聚焦: OCR结果引导Vision关注关键区域",
        "4. 错误纠正: 双轨验证，OCR和Vision互相校正",
        "5. 高置信度: 双重确认提升结果可信度",
        "6. 可解释性: 明确的分析依据和推理过程"
    ]
    
    for advantage in advantages:
        print(f"   ✅ {advantage}")
    
    # 展示技术细节
    print("\n🔧 关键技术实现:")
    tech_details = [
        "OCR文本智能分类: 正则表达式匹配构件编号、尺寸、材料、轴线",
        "增强提示生成: 基于OCR结果构建引导性Vision提示",
        "Vision引导分析: 让AI聚焦OCR发现的关键区域",
        "双轨结果融合: 智能合并OCR精确性和Vision语义理解",
        "全局坐标还原: 将切片结果映射回原图坐标系",
        "可视化验证: 生成标注图像验证识别结果"
    ]
    
    for i, detail in enumerate(tech_details, 1):
        print(f"   🔬 {i}. {detail}")

def demonstrate_ocr_classification():
    """演示OCR分类功能"""
    
    print("\n" + "="*80)
    print("🔍 OCR智能分类演示")
    
    # 模拟OCR提取结果
    mock_ocr_texts = [
        "B101",      # 构件编号
        "300x600",   # 尺寸规格
        "C30",       # 材料等级
        "轴线A-B",   # 轴线位置
        "KZ-12",     # 构件编号
        "HRB400",    # 材料等级
        "GL-03",     # 构件编号
        "200x400",   # 尺寸规格
        "1-2轴",     # 轴线位置
        "Q235",      # 材料等级
        "图纸标题",  # 无关文字
        "比例1:100"  # 无关文字
    ]
    
    print(f"\n📄 模拟OCR提取的文本（共{len(mock_ocr_texts)}项）:")
    for i, text in enumerate(mock_ocr_texts, 1):
        print(f"   {i:2d}. {text}")
    
    # 分类规则
    classification_rules = {
        "构件编号": [
            r'^[A-Z]{1,2}\d{2,4}$',  # B101, KZ01
            r'^[A-Z]{1,2}-\d{1,3}$', # B-1, KZ-12, GL-03
        ],
        "尺寸规格": [
            r'^\d{2,4}[xX×]\d{2,4}$',  # 300x600
        ],
        "材料等级": [
            r'^C\d{2}$',    # C30, C25
            r'^HRB\d{3}$',  # HRB400
            r'^Q\d{3}$',    # Q235
        ],
        "轴线位置": [
            r'^轴线[A-Z]-[A-Z]$',     # 轴线A-B
            r'^\d+-\d+轴$',           # 1-2轴
        ]
    }
    
    # 执行分类
    print(f"\n🧠 智能分类结果:")
    classification_results = {
        "构件编号": [],
        "尺寸规格": [],
        "材料等级": [],
        "轴线位置": [],
        "未知类型": []
    }
    
    import re
    
    for text in mock_ocr_texts:
        classified = False
        for category, patterns in classification_rules.items():
            for pattern in patterns:
                if re.match(pattern, text):
                    classification_results[category].append(text)
                    classified = True
                    break
            if classified:
                break
        
        if not classified:
            classification_results["未知类型"].append(text)
    
    # 显示分类结果
    category_icons = {
        "构件编号": "🏗️",
        "尺寸规格": "📏",
        "材料等级": "🧱",
        "轴线位置": "📍",
        "未知类型": "❓"
    }
    
    for category, texts in classification_results.items():
        if texts:
            icon = category_icons.get(category, "📋")
            print(f"   {icon} {category}: {', '.join(texts)}")

def demonstrate_enhanced_prompt_generation():
    """演示增强提示生成"""
    
    print("\n" + "="*80)
    print("🧠 增强提示生成演示")
    
    # 模拟分类后的OCR结果
    classified_ocr = {
        "构件编号": ["B101", "KZ-12"],
        "尺寸规格": ["300x600", "200x400"],
        "材料等级": ["C30", "HRB400"],
        "轴线位置": ["轴线A-B", "1-2轴"]
    }
    
    # 生成增强提示
    print(f"\n💬 为切片生成的增强提示:")
    print("-" * 60)
    
    prompt_template = """📄 当前图像为结构图切片（第2行第3列），尺寸 1024x1024

🔍 OCR识别的重要构件信息：
- 🏗️ 构件编号: {components}
- 📏 尺寸规格: {dimensions}
- 🧱 材料等级: {materials}
- 📍 轴线位置: {axes}

👁️ 请结合图像内容，重点分析：
1. 确认OCR识别的构件编号、尺寸、材料是否正确
2. 识别构件类型（梁、柱、板、墙、基础等）
3. 确定构件在图纸中的精确位置和边界
4. 补充OCR遗漏的重要信息

📋 返回JSON格式，包含：构件编号、类型、尺寸、材料、位置、置信度、边界框"""
    
    enhanced_prompt = prompt_template.format(
        components=", ".join(classified_ocr["构件编号"]),
        dimensions=", ".join(classified_ocr["尺寸规格"]),
        materials=", ".join(classified_ocr["材料等级"]),
        axes=", ".join(classified_ocr["轴线位置"])
    )
    
    print(enhanced_prompt)
    print("-" * 60)
    
    # 对比传统提示
    print(f"\n🆚 传统Vision提示对比:")
    print("-" * 60)
    
    traditional_prompt = """请识别图像中的建筑构件，包括：
- 构件编号和类型（梁、柱、板、墙等）
- 尺寸规格
- 材料等级
- 位置信息

返回JSON格式的构件列表。"""
    
    print(traditional_prompt)
    print("-" * 60)
    
    print(f"\n📈 增强提示的优势:")
    improvements = [
        "1. 精确引导: 明确告诉AI重点关注哪些区域",
        "2. 上下文信息: 提供切片位置和尺寸信息",
        "3. 验证逻辑: 要求AI确认OCR结果的正确性",
        "4. 补充要求: 提示AI发现OCR遗漏的信息",
        "5. 格式规范: 明确的JSON输出格式要求",
        "6. 分析步骤: 提供清晰的分析思路指导"
    ]
    
    for improvement in improvements:
        print(f"   ✅ {improvement}")

def demonstrate_dual_track_fusion():
    """演示双轨结果融合"""
    
    print("\n" + "="*80)
    print("🔀 双轨结果融合演示")
    
    # 模拟OCR结果
    ocr_result = {
        "texts": [
            {"text": "B101", "position": [[120, 300], [180, 300], [180, 340], [120, 340]], "confidence": 0.95},
            {"text": "300x600", "position": [[120, 350], [200, 350], [200, 380], [120, 380]], "confidence": 0.90},
            {"text": "C30", "position": [[250, 300], [280, 300], [280, 330], [250, 330]], "confidence": 0.88}
        ]
    }
    
    # 模拟Vision结果
    vision_result = {
        "components": [
            {
                "id": "B101",
                "type": "梁",
                "size": "300x600",
                "material": "C30",
                "location": "A-B/1-2轴",
                "confidence": 0.85,
                "bbox": {"x": 120, "y": 300, "width": 280, "height": 80}
            }
        ]
    }
    
    print(f"\n📊 融合前的双轨结果:")
    print(f"   🔍 OCR结果: {len(ocr_result['texts'])} 个文本项")
    print(f"   👁️ Vision结果: {len(vision_result['components'])} 个构件")
    
    # 融合逻辑
    print(f"\n🔄 融合过程:")
    fusion_steps = [
        "1. 位置匹配: 将OCR文本与Vision构件按位置对应",
        "2. 一致性检查: 验证OCR和Vision识别的一致性",
        "3. 置信度计算: 根据双轨一致性调整最终置信度",
        "4. 信息补全: 用Vision结果补充OCR缺失信息",
        "5. 冲突解决: 当两轨结果冲突时，选择置信度更高的"
    ]
    
    for step in fusion_steps:
        print(f"   ⚙️ {step}")
    
    # 模拟融合结果
    fused_result = {
        "id": "B101",
        "type": "梁",
        "size": "300x600",
        "material": "C30",
        "location": "A-B/1-2轴",
        "confidence": 0.92,  # 双轨融合后的置信度
        "verification": {
            "ocr_confidence": 0.95,
            "vision_confidence": 0.85,
            "consistency_score": 0.95,
            "fusion_confidence": 0.92
        },
        "source": "dual_track_fusion"
    }
    
    print(f"\n✅ 融合后的最终结果:")
    print(f"   📋 构件编号: {fused_result['id']}")
    print(f"   🏗️ 构件类型: {fused_result['type']}")
    print(f"   📏 尺寸规格: {fused_result['size']}")
    print(f"   🧱 材料等级: {fused_result['material']}")
    print(f"   📍 位置信息: {fused_result['location']}")
    print(f"   🎯 最终置信度: {fused_result['confidence']:.1%}")
    
    print(f"\n🔍 验证详情:")
    verification = fused_result['verification']
    print(f"   • OCR置信度: {verification['ocr_confidence']:.1%}")
    print(f"   • Vision置信度: {verification['vision_confidence']:.1%}")
    print(f"   • 一致性评分: {verification['consistency_score']:.1%}")
    print(f"   • 融合置信度: {verification['fusion_confidence']:.1%}")

def demonstrate_performance_comparison():
    """演示性能对比"""
    
    print("\n" + "="*80)
    print("📊 性能对比分析")
    
    # 模拟性能数据
    performance_data = {
        "传统OCR": {
            "准确率": "75%",
            "处理速度": "快",
            "API成本": "低",
            "适用场景": "简单图纸",
            "优势": "文字提取准确、速度快",
            "劣势": "无法理解图像语义"
        },
        "纯Vision": {
            "准确率": "80%",
            "处理速度": "中",
            "API成本": "中",
            "适用场景": "复杂图纸",
            "优势": "理解图像语义、识别构件",
            "劣势": "可能遗漏细节文字"
        },
        "双轨协同": {
            "准确率": "92%",
            "处理速度": "较慢",
            "API成本": "高",
            "适用场景": "高精度要求",
            "优势": "最高准确率、可解释性强",
            "劣势": "处理时间较长、成本较高"
        }
    }
    
    print(f"\n📈 各方法性能对比:")
    print("-" * 80)
    print(f"{'方法':<12} {'准确率':<8} {'速度':<8} {'成本':<8} {'适用场景':<12}")
    print("-" * 80)
    
    for method, metrics in performance_data.items():
        print(f"{method:<12} {metrics['准确率']:<8} {metrics['处理速度']:<8} "
              f"{metrics['API成本']:<8} {metrics['适用场景']:<12}")
    
    print(f"\n🎯 推荐策略:")
    recommendations = [
        "• 简单图纸（文字为主）→ 传统OCR",
        "• 复杂图纸（构件为主）→ 纯Vision",
        "• 高精度要求项目 → 双轨协同",
        "• 成本敏感项目 → 传统OCR + 后期人工验证",
        "• 时间敏感项目 → 纯Vision + 快速验证",
        "• 关键工程项目 → 双轨协同 + 多重验证"
    ]
    
    for rec in recommendations:
        print(f"   {rec}")

if __name__ == "__main__":
    print("🚀 双轨协同分析完整演示")
    print("="*80)
    
    # 1. 架构演示
    demonstrate_dual_track_architecture()
    
    # 2. OCR分类演示
    demonstrate_ocr_classification()
    
    # 3. 提示生成演示
    demonstrate_enhanced_prompt_generation()
    
    # 4. 结果融合演示
    demonstrate_dual_track_fusion()
    
    # 5. 性能对比
    demonstrate_performance_comparison()
    
    print("\n" + "="*80)
    print("✅ 双轨协同分析演示完成")
    
    print(f"\n🎉 总结:")
    print("双轨协同分析是OCR与Vision的完美结合，")
    print("通过智能分类、增强提示、结果融合等关键技术，")
    print("实现了文字精准提取与图像语义理解的协同工作，")
    print("为复杂工程图纸分析提供了最佳解决方案！")
    
    print(f"\n🔗 关键文件:")
    print("• backend/app/services/enhanced_grid_slice_analyzer.py")
    print("• backend/app/services/drawing_analysis_orchestrator.py")
    print("• backend/test_dual_track_analysis.py")
    print("• backend/enhanced_dual_track_demo.py") 