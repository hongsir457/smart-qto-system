#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双轨协同分析系统测试脚本
演示 OCR + Vision 协同分析流程
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dual_track_analysis_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_dual_track_analysis():
    """测试双轨协同分析系统"""
    
    logger.info("🚀 开始测试双轨协同分析系统")
    
    try:
        # 导入增强分析器
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        # 创建分析器实例
        analyzer = EnhancedGridSliceAnalyzer(
            slice_size=1024,
            overlap=128
        )
        
        # 准备测试数据
        test_image = "test_images/sample_floorplan.png"
        if not os.path.exists(test_image):
            os.makedirs("test_images", exist_ok=True)
            logger.warning(f"⚠️ 测试图像不存在: {test_image}")
            logger.info("请将测试图纸放置在 test_images/sample_floorplan.png")
            return
        
        # 图纸基本信息
        drawing_info = {
            "scale": "1:100",
            "drawing_number": "S03",
            "page_number": 1,
            "project_name": "双轨协同测试项目",
            "drawing_type": "结构图"
        }
        
        # 任务ID
        task_id = f"dual_track_test_{int(time.time())}"
        
        # 输出目录
        output_dir = f"temp_dual_track_{task_id}"
        
        logger.info(f"📐 测试参数:")
        logger.info(f"   - 图纸路径: {test_image}")
        logger.info(f"   - 分析方法: OCR + Vision 双轨协同")
        logger.info(f"   - 切片大小: {analyzer.slice_size}x{analyzer.slice_size}")
        logger.info(f"   - 输出目录: {output_dir}")
        
        # 执行双轨协同分析
        start_time = time.time()
        
        result = analyzer.analyze_drawing_with_dual_track(
            image_path=test_image,
            drawing_info=drawing_info,
            task_id=task_id,
            output_dir=output_dir
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 输出结果
        logger.info(f"⏱️ 分析耗时: {elapsed:.2f}秒")
        
        if result["success"]:
            logger.info("✅ 双轨协同分析完成！")
            
            # 输出分析结果统计
            qto_data = result["qto_data"]
            dual_track_metadata = result["dual_track_metadata"]
            
            logger.info(f"📊 分析结果统计:")
            logger.info(f"   - 总构件数: {qto_data['component_summary']['total_components']}")
            logger.info(f"   - 构件类型: {', '.join(qto_data['component_summary']['component_types'])}")
            
            # 双轨覆盖率统计
            coverage = qto_data['component_summary']['dual_track_coverage']
            logger.info(f"🔄 双轨覆盖率:")
            logger.info(f"   - 总切片数: {coverage['total_slices']}")
            logger.info(f"   - OCR分析切片: {coverage['ocr_analyzed_slices']}")
            logger.info(f"   - Vision分析切片: {coverage['vision_analyzed_slices']}")
            logger.info(f"   - 增强提示切片: {coverage['enhanced_slices']}")
            
            # OCR统计
            ocr_stats = dual_track_metadata.get("ocr_statistics", {})
            if ocr_stats:
                logger.info(f"🔍 OCR分析统计:")
                logger.info(f"   - 处理切片: {ocr_stats.get('processed_slices', 0)}")
                logger.info(f"   - 文本项总数: {ocr_stats.get('total_text_items', 0)}")
                logger.info(f"   - 成功率: {ocr_stats.get('success_rate', 0):.1%}")
            
            # 增强统计
            enhancement_stats = dual_track_metadata.get("enhancement_statistics", {})
            if enhancement_stats:
                logger.info(f"🧠 增强分析统计:")
                logger.info(f"   - 增强切片: {enhancement_stats.get('enhanced_slices', 0)}")
                classification_stats = enhancement_stats.get("classification_stats", {})
                logger.info(f"   - 构件编号: {classification_stats.get('component_id', 0)}")
                logger.info(f"   - 尺寸规格: {classification_stats.get('dimension', 0)}")
                logger.info(f"   - 材料等级: {classification_stats.get('material', 0)}")
                logger.info(f"   - 轴线位置: {classification_stats.get('axis', 0)}")
            
            # Vision统计
            vision_stats = dual_track_metadata.get("vision_statistics", {})
            if vision_stats:
                logger.info(f"👁️ Vision分析统计:")
                logger.info(f"   - 分析切片: {vision_stats.get('analyzed_slices', 0)}")
                logger.info(f"   - 增强分析: {vision_stats.get('enhanced_slices', 0)}")
                logger.info(f"   - 成功率: {vision_stats.get('success_rate', 0):.1%}")
                logger.info(f"   - 增强率: {vision_stats.get('enhancement_rate', 0):.1%}")
            
            # 输出构件示例
            components = qto_data["components"]
            logger.info(f"📋 构件示例:")
            for i, comp in enumerate(components[:5]):
                logger.info(f"   {i+1}. {comp['id']} - {comp['type']} ({comp['size']}) "
                           f"- {comp['material']} - 切片{comp['source_block']}")
            
            # 保存完整结果
            result_file = f"dual_track_result_{task_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 完整结果已保存: {result_file}")
                
        else:
            logger.error(f"❌ 分析失败: {result.get('error', '未知错误')}")
        
        # 演示OCR分类功能
        logger.info("\n" + "="*60)
        logger.info("🔍 OCR分类功能演示")
        demonstrate_ocr_classification(analyzer)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def demonstrate_ocr_classification(analyzer):
    """演示OCR文本分类功能"""
    
    try:
        # 模拟OCR结果
        from app.services.enhanced_grid_slice_analyzer import OCRTextItem
        
        mock_ocr_results = [
            OCRTextItem("B101", [[120, 300], [180, 300], [180, 340], [120, 340]], 0.95),
            OCRTextItem("300x600", [[120, 350], [200, 350], [200, 380], [120, 380]], 0.90),
            OCRTextItem("C30", [[250, 300], [280, 300], [280, 330], [250, 330]], 0.88),
            OCRTextItem("轴线A-B", [[50, 100], [150, 100], [150, 130], [50, 130]], 0.92),
            OCRTextItem("KZ-12", [[300, 400], [350, 400], [350, 430], [300, 430]], 0.93),
            OCRTextItem("HRB400", [[400, 200], [460, 200], [460, 230], [400, 230]], 0.87),
            OCRTextItem("图纸标题", [[100, 50], [200, 50], [200, 80], [100, 80]], 0.85),
        ]
        
        # 执行分类
        analyzer._classify_ocr_texts(mock_ocr_results)
        
        logger.info("📊 OCR文本分类结果:")
        
        # 按类别统计
        category_stats = {}
        for ocr_item in mock_ocr_results:
            category = ocr_item.category
            if category not in category_stats:
                category_stats[category] = []
            category_stats[category].append(ocr_item.text)
        
        category_names = {
            "component_id": "🏗️ 构件编号",
            "dimension": "📏 尺寸规格", 
            "material": "🧱 材料等级",
            "axis": "📍 轴线位置",
            "unknown": "❓ 未知类型"
        }
        
        for category, texts in category_stats.items():
            category_name = category_names.get(category, category)
            logger.info(f"   {category_name}: {', '.join(texts)}")
        
        # 演示增强提示生成
        logger.info("\n🧠 增强提示生成演示:")
        
        from app.services.enhanced_grid_slice_analyzer import EnhancedSliceInfo
        
        mock_slice_info = EnhancedSliceInfo(
            filename="slice_1_2.png",
            row=1,
            col=2, 
            x_offset=1024,
            y_offset=1024,
            source_page=1,
            width=1024,
            height=1024,
            slice_path="temp/slice_1_2.png",
            ocr_results=mock_ocr_results,
            enhanced_prompt=""
        )
        
        enhanced_prompt = analyzer._generate_enhanced_prompt(mock_slice_info)
        
        logger.info("生成的增强提示:")
        logger.info("-" * 40)
        logger.info(enhanced_prompt)
        logger.info("-" * 40)
        
    except Exception as e:
        logger.error(f"❌ OCR分类演示失败: {e}")

def compare_analysis_methods():
    """比较不同分析方法的效果"""
    logger.info("\n" + "="*60)
    logger.info("📊 分析方法效果对比")
    
    methods_comparison = {
        "传统OCR": {
            "优势": ["文本提取准确", "处理速度快", "成本低"],
            "劣势": ["无法理解图像语义", "构件识别有限", "依赖文字清晰度"],
            "适用场景": "文字密集型图纸、简单标注提取"
        },
        "纯Vision": {
            "优势": ["理解图像语义", "识别复杂构件", "综合分析能力强"],
            "劣势": ["可能忽略细节文字", "成本较高", "易受图像质量影响"],
            "适用场景": "复杂图纸、构件类型识别"
        },
        "双轨协同": {
            "优势": ["精准文字+语义理解", "互补增强", "高准确率", "可解释性强"],
            "劣势": ["处理时间较长", "系统复杂度高"],
            "适用场景": "高精度要求、复杂工程图纸、关键项目"
        }
    }
    
    for method, details in methods_comparison.items():
        logger.info(f"\n{method}:")
        logger.info(f"   ✅ 优势: {', '.join(details['优势'])}")
        logger.info(f"   ⚠️ 劣势: {', '.join(details['劣势'])}")
        logger.info(f"   🎯 适用: {details['适用场景']}")

if __name__ == "__main__":
    print("🔄 双轨协同分析系统测试")
    print("="*60)
    
    # 主测试
    test_dual_track_analysis()
    
    # 方法对比
    compare_analysis_methods()
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    
    # 使用说明
    print("\n📖 双轨协同分析优势:")
    print("• 🎯 OCR精准提取文字信息，Vision理解图像语义")
    print("• 🔍 OCR结果引导Vision聚焦关键区域")
    print("• 📈 互补增强，提升识别准确率")
    print("• 💡 可解释性强，分析过程可追溯")
    print("• 🚀 特别适合复杂工程图纸分析") 