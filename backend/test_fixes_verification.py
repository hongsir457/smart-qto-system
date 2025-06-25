#!/usr/bin/env python3
"""
验证两个关键问题的修复：
1. 切片标识重复问题
2. 缺失的_extract_ocr_from_slices_optimized方法
"""

import sys
import os
import logging
import math
from typing import Dict, Any, List

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_slice_id_uniqueness():
    """测试切片标识唯一性修复"""
    logger.info("🔍 测试1: 切片标识唯一性修复")
    
    try:
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        # 创建分析器实例
        analyzer = EnhancedGridSliceAnalyzer()
        
        # 模拟切片数据（故意创建可能重复的坐标）
        mock_slice_infos = []
        for i in range(24):  # 24个切片
            mock_slice_info = type('MockSlice', (), {
                'base64_data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
                'x': (i % 5) * 200,  # 可能导致重复的坐标
                'y': (i // 5) * 200,
                'width': 200,
                'height': 200
            })()
            mock_slice_infos.append(mock_slice_info)
        
        # 模拟shared_slice_results
        shared_slice_results = {
            'test_image.png': {
                'slice_infos': mock_slice_infos,
                'original_width': 1000,
                'original_height': 600
            }
        }
        
        # 测试复用切片
        result = analyzer._reuse_shared_slices(
            shared_slice_results, 
            'test_image.png', 
            {'page_number': 1}
        )
        
        if result.get('success'):
            # 检查切片标识唯一性
            slice_ids = [f"{s.row}_{s.col}" for s in analyzer.enhanced_slices]
            unique_ids = set(slice_ids)
            
            logger.info(f"📊 切片总数: {len(slice_ids)}")
            logger.info(f"📊 唯一标识数: {len(unique_ids)}")
            logger.info(f"📊 前5个标识: {slice_ids[:5]}")
            
            if len(slice_ids) == len(unique_ids):
                logger.info("✅ 测试1通过: 切片标识唯一性修复成功")
                return True
            else:
                logger.error(f"❌ 测试1失败: 仍有重复标识，重复数量: {len(slice_ids) - len(unique_ids)}")
                return False
        else:
            logger.error(f"❌ 测试1失败: 切片复用失败 - {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试1异常: {e}")
        return False

def test_missing_method_fix():
    """测试缺失方法的修复"""
    logger.info("🔍 测试2: 缺失方法修复验证")
    
    try:
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        # 创建分析器实例
        analyzer = EnhancedGridSliceAnalyzer()
        
        # 检查方法是否存在
        missing_methods = []
        required_methods = [
            '_extract_ocr_from_slices_optimized',
            '_extract_global_ocr_overview_optimized', 
            '_restore_global_coordinates_optimized'
        ]
        
        for method_name in required_methods:
            if not hasattr(analyzer, method_name):
                missing_methods.append(method_name)
            else:
                logger.info(f"✅ 方法存在: {method_name}")
        
        if missing_methods:
            logger.error(f"❌ 测试2失败: 缺失方法 {missing_methods}")
            return False
        
        logger.info("✅ 测试2通过: 所有缺失方法已修复")
        return True
            
    except Exception as e:
        logger.error(f"❌ 测试2异常: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始验证问题修复...")
    
    test_results = {
        "切片标识唯一性": test_slice_id_uniqueness(),
        "缺失方法修复": test_missing_method_fix()
    }
    
    logger.info("\n📊 测试结果汇总:")
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {test_name}: {status}")
    
    all_passed = all(test_results.values())
    
    if all_passed:
        logger.info("\n🎉 所有测试通过！问题修复验证成功")
    else:
        logger.error("\n⚠️ 部分测试失败，需要进一步检查")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 测试执行异常: {e}")
        sys.exit(1) 