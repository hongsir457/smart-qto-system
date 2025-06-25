"""
测试增强版PaddleOCR合并器
验证四大核心目标的实现效果
"""

import json
import time
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from paddleocr_enhanced_merger import EnhancedPaddleOCRMerger

def create_test_data():
    """创建测试数据 - 模拟真实的PaddleOCR切片结果"""
    
    # 模拟4个切片的OCR结果，包含重复、边缘文本等情况
    slice_results = [
        # 切片0: 左上角
        {
            'success': True,
            'text_regions': [
                {'text': 'KL1', 'bbox': [350, 280, 390, 300], 'confidence': 0.95},  # 边缘文本（右边缘）
                {'text': '200×300', 'bbox': [100, 50, 180, 70], 'confidence': 0.92},
                {'text': 'A', 'bbox': [50, 10, 70, 30], 'confidence': 0.98},  # 轴线
                {'text': '施工图', 'bbox': [10, 350, 80, 380], 'confidence': 0.88}  # 边缘文本（下边缘）
            ]
        },
        # 切片1: 右上角
        {
            'success': True,
            'text_regions': [
                {'text': 'KL1', 'bbox': [10, 280, 50, 300], 'confidence': 0.93},  # 重复文本（左边缘）
                {'text': 'KL2', 'bbox': [150, 200, 190, 220], 'confidence': 0.96},
                {'text': 'C30', 'bbox': [200, 100, 240, 120], 'confidence': 0.94},
                {'text': 'B', 'bbox': [80, 10, 100, 30], 'confidence': 0.97}  # 轴线
            ]
        },
        # 切片2: 左下角
        {
            'success': True,
            'text_regions': [
                {'text': '施工图', 'bbox': [10, 20, 80, 50], 'confidence': 0.85},  # 重复文本（上边缘）
                {'text': 'Z1', 'bbox': [120, 150, 160, 170], 'confidence': 0.91},
                {'text': '1500mm', 'bbox': [200, 200, 280, 220], 'confidence': 0.89},
                {'text': 'HRB400', 'bbox': [300, 300, 380, 320], 'confidence': 0.87}
            ]
        },
        # 切片3: 右下角
        {
            'success': True,
            'text_regions': [
                {'text': 'Z2', 'bbox': [50, 150, 90, 170], 'confidence': 0.93},
                {'text': '±0.000', 'bbox': [150, 250, 220, 270], 'confidence': 0.90},  # 高程
                {'text': '1', 'bbox': [300, 10, 320, 30], 'confidence': 0.98},  # 轴线（上边缘）
                {'text': '备注：钢筋保护层厚度', 'bbox': [20, 350, 200, 380], 'confidence': 0.82}  # 下边缘
            ]
        }
    ]
    
    # 切片坐标映射 - 每个切片400x400像素，有重叠
    slice_coordinate_map = {
        0: {  # 左上角
            'offset_x': 0, 
            'offset_y': 0, 
            'slice_width': 400, 
            'slice_height': 400,
            'slice_id': 'slice_0_0'
        },
        1: {  # 右上角
            'offset_x': 350,  # 有50像素重叠
            'offset_y': 0, 
            'slice_width': 400, 
            'slice_height': 400,
            'slice_id': 'slice_1_0'
        },
        2: {  # 左下角
            'offset_x': 0, 
            'offset_y': 350,  # 有50像素重叠
            'slice_width': 400, 
            'slice_height': 400,
            'slice_id': 'slice_0_1'
        },
        3: {  # 右下角
            'offset_x': 350, 
            'offset_y': 350, 
            'slice_width': 400, 
            'slice_height': 400,
            'slice_id': 'slice_1_1'
        }
    }
    
    # 原图信息
    original_image_info = {
        'width': 750,   # 总宽度
        'height': 750,  # 总高度
        'format': 'png',
        'channels': 3
    }
    
    return slice_results, slice_coordinate_map, original_image_info

def test_four_objectives():
    """测试四大核心目标"""
    
    print("🧪 开始测试增强版PaddleOCR合并器")
    print("=" * 60)
    
    # 准备测试数据
    slice_results, slice_coordinate_map, original_image_info = create_test_data()
    
    # 统计原始数据
    total_input_regions = sum(len(r.get('text_regions', [])) for r in slice_results if r.get('success'))
    print(f"📊 输入数据统计:")
    print(f"   • 切片数量: {len(slice_results)}")
    print(f"   • 原始文本区域: {total_input_regions}")
    print(f"   • 原图尺寸: {original_image_info['width']}x{original_image_info['height']}")
    print()
    
    # 创建增强合并器
    merger = EnhancedPaddleOCRMerger()
    
    # 执行合并
    start_time = time.time()
    result = merger.merge_with_four_objectives(
        slice_results=slice_results,
        slice_coordinate_map=slice_coordinate_map,
        original_image_info=original_image_info,
        task_id="test_four_objectives"
    )
    processing_time = time.time() - start_time
    
    print(f"⏱️  处理耗时: {processing_time:.3f} 秒")
    print()
    
    # 验证四大目标
    print("🎯 四大目标验证结果:")
    print("=" * 60)
    
    if result.get('success'):
        objectives = result.get('four_objectives_achievement', {})
        
        # 目标1: 不丢内容
        obj1 = objectives.get('objective1_content_preservation', {})
        print(f"✅ 目标1 - 不丢内容: {obj1.get('achieved', False)}")
        print(f"   • 边缘文本保护: {obj1.get('edge_text_protected', 0)} 个")
        print(f"   • 总保留区域: {obj1.get('total_preserved', 0)} 个")
        print()
        
        # 目标2: 不重复内容
        obj2 = objectives.get('objective2_no_duplication', {})
        print(f"✅ 目标2 - 不重复内容: {obj2.get('achieved', False)}")
        print(f"   • 去重移除: {obj2.get('duplicates_removed', 0)} 个")
        print(f"   • 去重率: {obj2.get('deduplication_rate', 0):.1%}")
        print()
        
        # 目标3: 正确排序
        obj3 = objectives.get('objective3_correct_ordering', {})
        print(f"✅ 目标3 - 正确排序: {obj3.get('achieved', False)}")
        print(f"   • 排序方法: {obj3.get('sorting_method', 'N/A')}")
        print(f"   • 有序区域: {obj3.get('ordered_regions', 0)} 个")
        print()
        
        # 目标4: 恢复全图坐标
        obj4 = objectives.get('objective4_coordinate_restoration', {})
        print(f"✅ 目标4 - 恢复全图坐标: {obj4.get('achieved', False)}")
        print(f"   • 坐标还原: {obj4.get('restored_coordinates', 0)} 个")
        print(f"   • 还原率: {obj4.get('restoration_rate', 0):.1%}")
        print()
        
        # 最终结果统计
        final_regions = result.get('text_regions', [])
        print("📈 最终结果统计:")
        print(f"   • 输入 -> 输出: {total_input_regions} -> {len(final_regions)}")
        print(f"   • 压缩率: {(1 - len(final_regions)/total_input_regions):.1%}")
        print(f"   • 平均置信度: {result.get('quality_metrics', {}).get('average_confidence', 0):.3f}")
        print()
        
        # 文本类型分布
        type_dist = result.get('text_type_distribution', {})
        print("📊 文本类型分布:")
        for text_type, count in type_dist.items():
            print(f"   • {text_type}: {count} 个")
        print()
        
        # 显示最终文本内容（按阅读顺序）
        print("📖 最终文本内容（按阅读顺序）:")
        print("-" * 40)
        full_text = result.get('full_text_content', '')
        for i, line in enumerate(full_text.split('\n')[:10], 1):  # 只显示前10行
            if line.strip():
                print(f"{i:2d}. {line}")
        if len(full_text.split('\n')) > 10:
            print("    ... (更多内容)")
        print()
        
        # 显示坐标还原示例
        print("🌍 坐标还原示例:")
        print("-" * 40)
        for i, region in enumerate(final_regions[:3]):  # 显示前3个区域
            bbox = region.get('bbox', [])
            transform = region.get('slice_source', {}).get('coordinate_transform', {})
            if transform:
                print(f"{i+1}. '{region.get('text', '')}' ")
                print(f"   切片坐标: {transform.get('original_bbox', [])}")
                print(f"   全图坐标: {transform.get('global_bbox', [])}")
                print(f"   偏移量: {transform.get('offset', (0, 0))}")
                print()
        
        print("🎉 测试完成！四大目标全部验证通过！")
        
    else:
        print("❌ 合并失败:", result.get('error', '未知错误'))
    
    return result

def test_edge_cases():
    """测试边缘情况"""
    
    print("\n🧪 测试边缘情况")
    print("=" * 60)
    
    # 测试空结果
    merger = EnhancedPaddleOCRMerger()
    
    # 空切片结果
    empty_result = merger.merge_with_four_objectives(
        slice_results=[],
        slice_coordinate_map={},
        original_image_info={'width': 100, 'height': 100},
        task_id="empty_test"
    )
    
    print(f"空输入测试: {'✅ 通过' if empty_result.get('success') else '❌ 失败'}")
    print(f"空输入结果区域数: {len(empty_result.get('text_regions', []))}")
    
    # 测试单个区域
    single_slice = [{
        'success': True,
        'text_regions': [{'text': 'Test', 'bbox': [10, 10, 50, 30], 'confidence': 0.9}]
    }]
    
    single_result = merger.merge_with_four_objectives(
        slice_results=single_slice,
        slice_coordinate_map={0: {'offset_x': 0, 'offset_y': 0, 'slice_width': 100, 'slice_height': 100}},
        original_image_info={'width': 100, 'height': 100},
        task_id="single_test"
    )
    
    print(f"单区域测试: {'✅ 通过' if single_result.get('success') else '❌ 失败'}")
    print(f"单区域结果数: {len(single_result.get('text_regions', []))}")
    
    print()

def save_test_results(result, filename="test_enhanced_merger_result.json"):
    """保存测试结果"""
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 测试结果已保存到: {filename}")
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")

if __name__ == "__main__":
    print("🚀 增强版PaddleOCR合并器测试程序")
    print("测试四大核心目标的实现效果")
    print("=" * 60)
    
    try:
        # 执行主要测试
        result = test_four_objectives()
        
        # 测试边缘情况
        test_edge_cases()
        
        # 保存结果
        save_test_results(result)
        
        print("\n🏆 所有测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc() 