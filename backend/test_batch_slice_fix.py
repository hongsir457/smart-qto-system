#!/usr/bin/env python3
"""
批次切片索引修复验证测试
验证每个批次是否处理了正确的切片范围
"""

import os
import sys
import logging
import time
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_batch_slice_indexing():
    """测试批次切片索引修复"""
    logger.info("🚀 开始测试批次切片索引修复")
    
    try:
        from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
        
        # 创建模拟的智能切片结果
        mock_shared_slice_results = create_mock_shared_slice_results()
        
        # 测试1: 验证单批次处理（应该处理所有24个切片）
        logger.info("\n🧪 测试1: 单批次处理")
        analyzer = EnhancedGridSliceAnalyzer()
        
        test_image_path = "/tmp/test_drawing.png"
        drawing_info = {
            "scale": "1:100",
            "drawing_number": "S03",
            "page_number": 1,
            "project_name": "批次测试项目",
            "drawing_type": "结构图"
        }
        
        # 模拟单批次复用
        result = analyzer._reuse_shared_slices(
            mock_shared_slice_results, 
            test_image_path, 
            drawing_info
        )
        
        if result.get("success"):
            logger.info(f"✅ 单批次复用成功: {result.get('slice_count')} 个切片")
            
            # 验证切片索引
            rows = [s.row for s in analyzer.enhanced_slices]
            cols = [s.col for s in analyzer.enhanced_slices]
            
            logger.info(f"📍 切片行范围: {min(rows)} - {max(rows)}")
            logger.info(f"📍 切片列范围: {min(cols)} - {max(cols)}")
            logger.info(f"📍 前5个切片: {[f'{s.row}_{s.col}' for s in analyzer.enhanced_slices[:5]]}")
            logger.info(f"📍 后5个切片: {[f'{s.row}_{s.col}' for s in analyzer.enhanced_slices[-5:]]}")
            
            # 验证是否有重复的切片标识
            slice_ids = [f"{s.row}_{s.col}" for s in analyzer.enhanced_slices]
            unique_ids = set(slice_ids)
            
            if len(slice_ids) == len(unique_ids):
                logger.info("✅ 切片标识唯一性检查通过")
            else:
                logger.error(f"❌ 发现重复的切片标识: {len(slice_ids)} vs {len(unique_ids)}")
                
        else:
            logger.error(f"❌ 单批次复用失败: {result.get('error')}")
            return False
            
        logger.info("\n✅ 批次切片索引修复测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_mock_shared_slice_results() -> Dict[str, Any]:
    """创建模拟的智能切片结果"""
    import base64
    
    slice_infos = []
    
    # 创建6x4网格的24个切片
    rows, cols = 4, 6
    slice_size = 2048
    
    for row in range(rows):
        for col in range(cols):
            slice_info = type('SliceInfo', (), {
                'slice_id': f'slice_{row}_{col}',
                'x': col * slice_size,
                'y': row * slice_size,
                'width': slice_size,
                'height': slice_size,
                'base64_data': base64.b64encode(b"mock_image_data").decode()
            })()
            
            slice_infos.append(slice_info)
    
    return {
        "/tmp/test_drawing.png": {
            "slice_infos": slice_infos,
            "original_width": cols * slice_size,  # 12288
            "original_height": rows * slice_size,  # 8192
            "sliced": True,
            "slice_count": len(slice_infos)
        }
    }

if __name__ == "__main__":
    success = test_batch_slice_indexing()
    if success:
        logger.info("🎉 所有测试通过！")
        sys.exit(0)
    else:
        logger.error("💥 测试失败！")
        sys.exit(1) 