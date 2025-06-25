#!/usr/bin/env python3
"""快速测试批次切片索引修复"""

import sys
import os
sys.path.insert(0, '.')

from app.services.enhanced_grid_slice_analyzer import EnhancedGridSliceAnalyzer
import base64

def test_batch_fix():
    print("🚀 测试批次切片索引修复")
    
    # 创建模拟切片数据
    slice_infos = []
    for row in range(4):
        for col in range(6):
            slice_info = type('SliceInfo', (), {
                'slice_id': f'slice_{row}_{col}',
                'x': col * 2048,
                'y': row * 2048,
                'width': 2048,
                'height': 2048,
                'base64_data': base64.b64encode(b'mock_data').decode()
            })()
            slice_infos.append(slice_info)

    mock_results = {
        '/tmp/test.png': {
            'slice_infos': slice_infos,
            'original_width': 12288,
            'original_height': 8192
        }
    }

    # 测试修复效果
    analyzer = EnhancedGridSliceAnalyzer()
    result = analyzer._reuse_shared_slices(mock_results, '/tmp/test.png', {})

    if result.get('success'):
        rows = [s.row for s in analyzer.enhanced_slices]
        cols = [s.col for s in analyzer.enhanced_slices]
        slice_ids = [f'{s.row}_{s.col}' for s in analyzer.enhanced_slices]
        
        print(f'✅ 测试成功: {len(analyzer.enhanced_slices)} 个切片')
        print(f'📍 行范围: {min(rows)}-{max(rows)}, 列范围: {min(cols)}-{max(cols)}')
        print(f'📍 前5个切片: {slice_ids[:5]}')
        print(f'📍 后5个切片: {slice_ids[-5:]}')
        print(f'📍 切片唯一性: {len(slice_ids)} == {len(set(slice_ids))} = {len(slice_ids) == len(set(slice_ids))}')
        
        # 验证坐标计算
        print("\n📐 坐标验证:")
        for i in range(min(3, len(analyzer.enhanced_slices))):
            s = analyzer.enhanced_slices[i]
            expected_row = s.y_offset // 2048
            expected_col = s.x_offset // 2048
            print(f'   切片{i}: 位置({s.x_offset},{s.y_offset}) -> 计算({s.row},{s.col}) vs 期望({expected_row},{expected_col})')
            
        return True
    else:
        print(f'❌ 测试失败: {result.get("error")}')
        return False

if __name__ == "__main__":
    success = test_batch_fix()
    if success:
        print("\n🎉 批次切片索引修复验证通过！")
    else:
        print("\n💥 批次切片索引修复验证失败！") 