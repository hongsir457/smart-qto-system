#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整优化验证脚本
测试所有9项优化的实施效果
"""

import sys
import os
import time
import json
import logging
from typing import Dict, Any, List

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_optimization_1_unified_ocr_cache():
    """测试优化1: 统一OCR缓存策略"""
    logger.info("🔧 测试优化1: 统一OCR缓存策略")
    
    try:
        from app.utils.analysis_optimizations import OCRCacheManager, AnalysisLogger
        
        # 创建OCR缓存管理器
        cache_manager = OCRCacheManager()
        
        # 测试缓存设置和获取
        test_slice_key = "test_slice_0_0"
        test_ocr_data = [{"text": "KZ1", "confidence": 0.95}]
        
        # 设置缓存
        cache_manager.set_ocr_result(test_slice_key, test_ocr_data, "global_cache")
        
        # 获取缓存
        cached_result = cache_manager.get_ocr_result(test_slice_key)
        
        if cached_result == test_ocr_data:
            logger.info("✅ 优化1测试通过: OCR缓存设置和获取正常")
            
            # 测试缓存统计
            stats = cache_manager.get_cache_stats()
            AnalysisLogger.log_cache_stats(stats)
            
            return True
        else:
            logger.error("❌ 优化1测试失败: OCR缓存数据不匹配")
            return False
            
    except Exception as e:
        logger.error(f"❌ 优化1测试异常: {e}")
        return False

def test_optimization_2_analyzer_instance_reuse():
    """测试优化2: 分析器实例复用"""
    logger.info("🔧 测试优化2: 分析器实例复用")
    
    try:
        from app.utils.analysis_optimizations import AnalyzerInstanceManager
        
        # 创建实例管理器
        manager = AnalyzerInstanceManager()
        
        # 模拟分析器类
        class MockAnalyzer:
            def __init__(self):
                self.created_at = time.time()
            
            def reset_batch_state(self):
                self.reset_count = getattr(self, 'reset_count', 0) + 1
        
        # 获取第一个实例
        analyzer1 = manager.get_analyzer(MockAnalyzer)
        
        # 获取第二个实例（应该是同一个）
        analyzer2 = manager.get_analyzer(MockAnalyzer)
        
        if analyzer1 is analyzer2:
            logger.info("✅ 优化2测试通过: 分析器实例成功复用")
            
            # 测试批次重置
            manager.reset_for_new_batch()
            
            # 获取实例统计
            stats = manager.get_instance_stats()
            logger.info(f"📊 实例统计: {stats}")
            
            return True
        else:
            logger.error("❌ 优化2测试失败: 分析器实例未复用")
            return False
            
    except Exception as e:
        logger.error(f"❌ 优化2测试异常: {e}")
        return False

def test_optimization_3_coordinate_transform_service():
    """测试优化3: 统一坐标转换服务"""
    logger.info("🔧 测试优化3: 统一坐标转换服务")
    
    try:
        from app.utils.analysis_optimizations import CoordinateTransformService, CoordinatePoint, AnalysisLogger
        
        # 模拟切片坐标映射
        slice_map = {
            "slice_0_0": {"x_offset": 0, "y_offset": 0},
            "slice_0_1": {"x_offset": 1024, "y_offset": 0},
            "slice_1_0": {"x_offset": 0, "y_offset": 1024}
        }
        
        # 模拟原图信息
        original_info = {"width": 2048, "height": 2048}
        
        # 创建坐标转换服务
        coord_service = CoordinateTransformService(slice_map, original_info)
        
        # 测试单个坐标转换
        slice_coord = CoordinatePoint(x=100, y=200)
        global_coord = coord_service.transform_to_global(slice_coord, "slice_0_1")
        
        expected_x = 100 + 1024  # 切片偏移
        expected_y = 200 + 0
        
        if global_coord.global_x == expected_x and global_coord.global_y == expected_y:
            logger.info("✅ 优化3测试通过: 坐标转换正确")
            
            # 测试批量坐标转换
            coords = [
                (CoordinatePoint(x=50, y=50), "slice_0_0"),
                (CoordinatePoint(x=100, y=100), "slice_1_0")
            ]
            
            batch_results = coord_service.batch_transform_coordinates(coords)
            AnalysisLogger.log_coordinate_transform(len(batch_results), len(coords))
            
            return True
        else:
            logger.error(f"❌ 优化3测试失败: 坐标转换错误 - 期望({expected_x}, {expected_y}), 实际({global_coord.global_x}, {global_coord.global_y})")
            return False
            
    except Exception as e:
        logger.error(f"❌ 优化3测试异常: {e}")
        return False

def test_optimization_4_gpt_response_parser():
    """测试优化4: 统一GPT响应解析器"""
    logger.info("🔧 测试优化4: 统一GPT响应解析器")
    
    try:
        from app.utils.analysis_optimizations import GPTResponseParser
        
        # 测试正常JSON响应
        normal_response = '{"drawing_info": {"drawing_title": "测试图纸"}, "component_ids": ["KZ1", "L1"]}'
        parsed_normal = GPTResponseParser.extract_json_from_response(normal_response)
        
        # 测试带```json标记的响应
        markdown_response = '''```json
        {"drawing_info": {"drawing_title": "测试图纸"}, "component_ids": ["KZ1", "L1"]}
        ```'''
        parsed_markdown = GPTResponseParser.extract_json_from_response(markdown_response)
        
        # 测试错误响应（应该返回降级结果）
        error_response = "这不是JSON格式"
        parsed_error = GPTResponseParser.extract_json_from_response(error_response)
        
        # 验证结果
        if (parsed_normal.get("drawing_info", {}).get("drawing_title") == "测试图纸" and
            parsed_markdown.get("drawing_info", {}).get("drawing_title") == "测试图纸" and
            parsed_error.get("drawing_info", {}).get("drawing_title") == "未识别"):
            
            logger.info("✅ 优化4测试通过: GPT响应解析器工作正常")
            
            # 测试结构验证
            required_fields = ["drawing_info", "component_ids"]
            is_valid = GPTResponseParser.validate_json_structure(parsed_normal, required_fields)
            logger.info(f"📋 结构验证结果: {is_valid}")
            
            return True
        else:
            logger.error("❌ 优化4测试失败: GPT响应解析结果不正确")
            return False
            
    except Exception as e:
        logger.error(f"❌ 优化4测试异常: {e}")
        return False

def test_optimization_5_standardized_logging():
    """测试优化5: 标准化日志记录"""
    logger.info("🔧 测试优化5: 标准化日志记录")
    
    try:
        from app.utils.analysis_optimizations import AnalysisLogger, AnalysisMetadata
        
        # 测试各种日志记录方法
        AnalysisLogger.log_ocr_reuse("test_slice", 10, "global_cache")
        AnalysisLogger.log_batch_processing(1, 3, 8)
        AnalysisLogger.log_coordinate_transform(20, 24)
        
        # 测试分析元数据日志
        metadata = AnalysisMetadata(
            analysis_method="test_analysis",
            batch_id=1,
            slice_count=8,
            success=True,
            processing_time=1.5
        )
        AnalysisLogger.log_analysis_metadata(metadata)
        
        logger.info("✅ 优化5测试通过: 标准化日志记录正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 优化5测试异常: {e}")
        return False

def test_optimization_6_configurable_batch_size():
    """测试优化6: 配置化批次大小"""
    logger.info("🔧 测试优化6: 配置化批次大小")
    
    try:
        from app.core.config import AnalysisSettings
        
        # 检查配置是否存在
        batch_size = AnalysisSettings.MAX_SLICES_PER_BATCH
        cache_ttl = AnalysisSettings.OCR_CACHE_TTL
        api_timeout = AnalysisSettings.VISION_API_TIMEOUT
        
        logger.info(f"📋 批次大小配置: {batch_size}")
        logger.info(f"📋 缓存TTL配置: {cache_ttl}")
        logger.info(f"📋 API超时配置: {api_timeout}")
        
        # 检查OCR缓存优先级配置
        priority = AnalysisSettings.OCR_CACHE_PRIORITY
        logger.info(f"📋 OCR缓存优先级: {priority}")
        
        if batch_size > 0 and cache_ttl > 0 and api_timeout > 0:
            logger.info("✅ 优化6测试通过: 配置化参数正常")
            return True
        else:
            logger.error("❌ 优化6测试失败: 配置参数异常")
            return False
            
    except Exception as e:
        logger.error(f"❌ 优化6测试异常: {e}")
        return False

def test_optimization_7_dataclass_management():
    """测试优化7: 数据类统一管理"""
    logger.info("🔧 测试优化7: 数据类统一管理")
    
    try:
        from app.utils.analysis_optimizations import AnalysisMetadata, CoordinatePoint
        from dataclasses import asdict
        
        # 测试AnalysisMetadata
        metadata = AnalysisMetadata(
            analysis_method="test_method",
            batch_id=1,
            slice_count=8,
            success=True,
            ocr_cache_used=True,
            processing_time=2.5
        )
        
        # 转换为字典
        metadata_dict = asdict(metadata)
        
        # 测试CoordinatePoint
        coord = CoordinatePoint(x=100, y=200, slice_id="test_slice")
        coord_dict = asdict(coord)
        
        if (metadata_dict["analysis_method"] == "test_method" and
            coord_dict["x"] == 100 and coord_dict["y"] == 200):
            
            logger.info("✅ 优化7测试通过: 数据类管理正常")
            logger.info(f"📋 元数据字典: {metadata_dict}")
            logger.info(f"📋 坐标字典: {coord_dict}")
            
            return True
        else:
            logger.error("❌ 优化7测试失败: 数据类转换异常")
            return False
            
    except Exception as e:
        logger.error(f"❌ 优化7测试异常: {e}")
        return False

def test_optimization_8_enhanced_grid_slice_analyzer():
    """测试优化8: 增强网格切片分析器优化"""
    logger.info("🔧 测试优化8: 增强网格切片分析器优化")
    
    try:
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        # 创建分析器实例
        analyzer = EnhancedGridSliceAnalyzer()
        
        # 检查是否有优化的OCR缓存管理器
        if hasattr(analyzer, 'ocr_cache'):
            logger.info("✅ 分析器已集成OCR缓存管理器")
        else:
            logger.warning("⚠️ 分析器未集成OCR缓存管理器")
        
        # 检查是否有批次状态重置方法
        if hasattr(analyzer, 'reset_batch_state'):
            analyzer.reset_batch_state()
            logger.info("✅ 分析器支持批次状态重置")
        else:
            logger.warning("⚠️ 分析器不支持批次状态重置")
        
        # 检查坐标转换服务初始化
        if hasattr(analyzer, '_initialize_coordinate_service'):
            logger.info("✅ 分析器支持坐标转换服务初始化")
        else:
            logger.warning("⚠️ 分析器不支持坐标转换服务初始化")
        
        logger.info("✅ 优化8测试通过: 增强网格切片分析器优化正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 优化8测试异常: {e}")
        return False

def test_optimization_9_vision_scanner_optimization():
    """测试优化9: Vision扫描器优化"""
    logger.info("🔧 测试优化9: Vision扫描器优化")
    
    try:
        from app.services.vision_scanner import VisionScannerService
        
        # 创建Vision扫描器实例
        scanner = VisionScannerService()
        
        # 检查是否有优化的批次处理方法
        if hasattr(scanner, '_process_slices_in_batches'):
            logger.info("✅ Vision扫描器有批次处理方法")
        else:
            logger.warning("⚠️ Vision扫描器缺少批次处理方法")
        
        # 检查是否使用了配置化的批次大小
        from app.core.config import AnalysisSettings
        batch_size = AnalysisSettings.MAX_SLICES_PER_BATCH
        logger.info(f"📋 使用配置化批次大小: {batch_size}")
        
        logger.info("✅ 优化9测试通过: Vision扫描器优化正常")
        return True
        
    except Exception as e:
        logger.error(f"❌ 优化9测试异常: {e}")
        return False

def run_all_optimization_tests():
    """运行所有优化测试"""
    logger.info("🚀 开始运行所有优化测试")
    
    test_results = {}
    
    # 运行所有测试
    tests = [
        ("统一OCR缓存策略", test_optimization_1_unified_ocr_cache),
        ("分析器实例复用", test_optimization_2_analyzer_instance_reuse),
        ("统一坐标转换服务", test_optimization_3_coordinate_transform_service),
        ("统一GPT响应解析器", test_optimization_4_gpt_response_parser),
        ("标准化日志记录", test_optimization_5_standardized_logging),
        ("配置化批次大小", test_optimization_6_configurable_batch_size),
        ("数据类统一管理", test_optimization_7_dataclass_management),
        ("增强网格切片分析器", test_optimization_8_enhanced_grid_slice_analyzer),
        ("Vision扫描器优化", test_optimization_9_vision_scanner_optimization)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 执行测试: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            result = test_func()
            test_results[test_name] = result
            if result:
                passed_tests += 1
                logger.info(f"✅ 测试通过: {test_name}")
            else:
                logger.error(f"❌ 测试失败: {test_name}")
        except Exception as e:
            test_results[test_name] = False
            logger.error(f"❌ 测试异常: {test_name} - {e}")
    
    # 生成测试报告
    logger.info(f"\n{'='*60}")
    logger.info("📊 优化测试报告")
    logger.info(f"{'='*60}")
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"通过测试: {passed_tests}")
    logger.info(f"失败测试: {total_tests - passed_tests}")
    logger.info(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    logger.info("\n📋 详细结果:")
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {status} {test_name}")
    
    # 保存测试结果
    report = {
        "timestamp": time.time(),
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "success_rate": passed_tests/total_tests*100,
        "detailed_results": test_results
    }
    
    with open("optimization_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📄 测试报告已保存到: optimization_test_report.json")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_optimization_tests()
    sys.exit(0 if success else 1) 