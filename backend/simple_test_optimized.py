"""
简化的优化系统测试
"""

import asyncio
import os
import json
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_adaptive_slicing():
    """测试自适应切片引擎"""
    logger.info("🔧 测试自适应切片引擎...")
    
    try:
        from app.services.adaptive_slicing_engine import AdaptiveSlicingEngine
        
        engine = AdaptiveSlicingEngine()
        
        # 创建模拟图片路径
        mock_image_path = "mock_image.png"
        
        # 创建一个简单的模拟文件
        with open(mock_image_path, 'w') as f:
            f.write("mock image")
        
        result = engine.adaptive_slice(mock_image_path, "test_slices")
        
        if result["success"]:
            logger.info(f"✅ 自适应切片测试成功: {result['slice_count']} 个切片")
        else:
            logger.error(f"❌ 自适应切片测试失败: {result.get('error')}")
        
        # 清理
        if os.path.exists(mock_image_path):
            os.remove(mock_image_path)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 自适应切片测试异常: {e}")
        return {"success": False, "error": str(e)}

async def test_unified_ocr():
    """测试统一OCR管道"""
    logger.info("🔧 测试统一OCR管道...")
    
    try:
        from app.services.unified_ocr_pipeline import UnifiedOCRPipeline
        
        pipeline = UnifiedOCRPipeline()
        
        # 模拟切片信息
        slice_infos = [
            {
                "slice_id": "test_slice_1",
                "filename": "slice_1.png",
                "slice_path": "mock_path_1",
                "x_offset": 0,
                "y_offset": 0,
                "width": 512,
                "height": 512
            },
            {
                "slice_id": "test_slice_2", 
                "filename": "slice_2.png",
                "slice_path": "mock_path_2",
                "x_offset": 512,
                "y_offset": 0,
                "width": 512,
                "height": 512
            }
        ]
        
        result = await pipeline.process_slices(slice_infos, "test_task")
        
        if result.stage == "unified_ocr_complete":
            logger.info(f"✅ 统一OCR测试成功: 质量评分 {result.quality_metrics['overall_quality']:.3f}")
        else:
            logger.error(f"❌ 统一OCR测试失败: {result.stage}")
        
        return {"success": result.stage == "unified_ocr_complete", "result": result}
        
    except Exception as e:
        logger.error(f"❌ 统一OCR测试异常: {e}")
        return {"success": False, "error": str(e)}

async def test_cross_modal_validation():
    """测试跨模态验证"""
    logger.info("🔧 测试跨模态验证引擎...")
    
    try:
        from app.services.cross_modal_validation_engine import CrossModalValidationEngine
        
        engine = CrossModalValidationEngine()
        
        # 模拟OCR结果
        ocr_output = {
            "slice_results": [
                {
                    "slice_id": "slice_1",
                    "raw_text": "C1",
                    "coordinates": {"x": 100, "y": 100, "width": 50, "height": 50},
                    "confidence": 0.9
                }
            ]
        }
        
        # 模拟Vision结果
        vision_output = {
            "detected_components": [
                {
                    "label": "C1",
                    "type": "column",
                    "bbox": {"x": 105, "y": 105, "width": 45, "height": 45},
                    "confidence": 0.85
                }
            ]
        }
        
        result = await engine.validate_cross_modal_results(ocr_output, vision_output, "test_task")
        
        if result["success"]:
            metrics = result["validation_report"]["overall_metrics"]
            logger.info(f"✅ 跨模态验证测试成功: 对齐度 {metrics['alignment_confidence']:.3f}")
        else:
            logger.error(f"❌ 跨模态验证测试失败: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 跨模态验证测试异常: {e}")
        return {"success": False, "error": str(e)}

async def test_intelligent_fusion():
    """测试智能融合引擎"""
    logger.info("🔧 测试智能融合引擎...")
    
    try:
        from app.services.intelligent_fusion_engine import IntelligentFusionEngine
        
        engine = IntelligentFusionEngine()
        
        # 模拟输入数据
        ocr_results = {
            "slice_results": [
                {
                    "slice_id": "slice_1",
                    "raw_text": "C1",
                    "coordinates": {"x": 100, "y": 100, "width": 50, "height": 50},
                    "confidence": 0.9
                }
            ]
        }
        
        vision_results = {
            "detected_components": [
                {
                    "label": "C1",
                    "type": "column",
                    "bbox": {"x": 105, "y": 105, "width": 45, "height": 45},
                    "confidence": 0.85
                }
            ]
        }
        
        validation_report = {
            "overall_metrics": {
                "alignment_confidence": 0.8,
                "consistency_rate": 0.9
            }
        }
        
        result = await engine.fuse_multi_modal_results(
            ocr_results, vision_results, validation_report, "test_task"
        )
        
        if result["success"]:
            metrics = result["fusion_report"]["quality_metrics"]
            logger.info(f"✅ 智能融合测试成功: 质量评分 {metrics['overall_quality']:.3f}")
        else:
            logger.error(f"❌ 智能融合测试失败: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 智能融合测试异常: {e}")
        return {"success": False, "error": str(e)}

async def test_standardized_output():
    """测试标准化输出引擎"""
    logger.info("🔧 测试标准化输出引擎...")
    
    try:
        from app.services.standardized_output_engine import StandardizedOutputEngine
        
        engine = StandardizedOutputEngine()
        
        # 模拟融合构件
        fused_components = [
            {
                "component_id": "test_column_1",
                "type": "column",
                "label": "C1",
                "dimensions": {"length": 0.4, "width": 0.4, "height": 3.0},
                "confidence": 0.9
            },
            {
                "component_id": "test_beam_1",
                "type": "beam", 
                "label": "L1",
                "dimensions": {"length": 6.0, "width": 0.3, "height": 0.5},
                "confidence": 0.85
            }
        ]
        
        project_info = {
            "project_name": "优化系统测试项目",
            "drawing_number": "TEST-001",
            "scale": "1:100"
        }
        
        result = await engine.generate_quantity_list(fused_components, project_info, "test_task")
        
        if result["success"]:
            summary = result["quantity_list"]["total_summary"]
            logger.info(f"✅ 标准化输出测试成功: {summary['total_components']} 个构件")
        else:
            logger.error(f"❌ 标准化输出测试失败: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 标准化输出测试异常: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """主测试函数"""
    logger.info("🚀 开始优化系统简化测试")
    start_time = time.time()
    
    test_results = {}
    
    # 测试各个组件
    test_results["adaptive_slicing"] = await test_adaptive_slicing()
    test_results["unified_ocr"] = await test_unified_ocr()
    test_results["cross_modal_validation"] = await test_cross_modal_validation()
    test_results["intelligent_fusion"] = await test_intelligent_fusion()
    test_results["standardized_output"] = await test_standardized_output()
    
    total_time = time.time() - start_time
    
    # 统计结果
    success_count = sum(1 for result in test_results.values() if result.get("success", False))
    total_tests = len(test_results)
    
    logger.info("=" * 60)
    logger.info(f"📊 优化系统测试结果汇总:")
    logger.info(f"   ✅ 成功: {success_count}/{total_tests}")
    logger.info(f"   ⏱️  总用时: {total_time:.2f}s")
    
    for test_name, result in test_results.items():
        status = "✅" if result.get("success", False) else "❌"
        logger.info(f"   {status} {test_name}: {'成功' if result.get('success', False) else '失败'}")
    
    logger.info("=" * 60)
    
    if success_count == total_tests:
        logger.info("🎉 所有优化组件测试通过！系统优化成功！")
    else:
        logger.warning(f"⚠️ {total_tests - success_count} 个组件测试失败，需要进一步调试")
    
    # 保存测试报告
    report = {
        "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_time": total_time,
        "success_rate": success_count / total_tests,
        "test_results": test_results,
        "optimization_summary": {
            "adaptive_slicing": "动态切片策略，提升切片适应性",
            "unified_ocr": "标准化OCR处理流程，提高效率",
            "cross_modal_validation": "跨模态验证，提升准确性",
            "intelligent_fusion": "智能融合，解决冲突",
            "standardized_output": "规范化输出，符合标准"
        }
    }
    
    os.makedirs("test_output", exist_ok=True)
    with open("test_output/optimization_test_report.json", 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info("📋 测试报告已保存: test_output/optimization_test_report.json")

if __name__ == "__main__":
    asyncio.run(main()) 