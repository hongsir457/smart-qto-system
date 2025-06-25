#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果合并器功能测试脚本
"""

import sys
import os
import json
from typing import Dict, List, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.services.result_merger_service import ResultMergerService

def create_mock_ocr_slice_results() -> List[Dict[str, Any]]:
    """创建模拟的OCR切片结果"""
    return [
        {
            'success': True,
            'text_regions': [
                {
                    'text': '建筑工程施工图',
                    'bbox': [100, 50, 300, 80],
                    'confidence': 0.95
                },
                {
                    'text': 'KZ-1',
                    'bbox': [150, 200, 200, 230],
                    'confidence': 0.92
                },
                {
                    'text': '500×500',
                    'bbox': [150, 240, 220, 270],
                    'confidence': 0.88
                }
            ],
            'all_text': '建筑工程施工图\nKZ-1\n500×500'
        },
        {
            'success': True,
            'text_regions': [
                {
                    'text': 'L-1',
                    'bbox': [50, 100, 100, 130],
                    'confidence': 0.90
                },
                {
                    'text': '300×600',
                    'bbox': [50, 140, 120, 170],
                    'confidence': 0.87
                },
                {
                    'text': 'C30',
                    'bbox': [50, 180, 80, 210],
                    'confidence': 0.85
                }
            ],
            'all_text': 'L-1\n300×600\nC30'
        }
    ]

def create_mock_vision_slice_results() -> List[Dict[str, Any]]:
    """创建模拟的Vision分析结果"""
    return [
        {
            'success': True,
            'qto_data': {
                'drawing_info': {
                    'title': '某工程结构施工图',
                    'scale': '1:100',
                    'drawing_number': 'S-01'
                },
                'project_analysis': {
                    'project_name': '测试工程项目',
                    'company_name': '某建设公司'
                },
                'components': [
                    {
                        'component_id': 'KZ-1',
                        'component_type': '框架柱',
                        'dimensions': {
                            'width': 0.5,
                            'height': 0.5,
                            'length': 3.6
                        },
                        'position': [150, 200],
                        'bbox': [130, 180, 220, 270],
                        'quantity': 1,
                        'reinforcement': {
                            'main': '8Φ25',
                            'stirrup': 'Φ8@200'
                        }
                    }
                ],
                'raw_text_summary': '识别到框架柱KZ-1，尺寸500×500，主筋8Φ25，箍筋Φ8@200'
            }
        },
        {
            'success': True,
            'qto_data': {
                'drawing_info': {
                    'title': '某工程结构施工图',
                    'scale': '1:100'
                },
                'components': [
                    {
                        'component_id': 'L-1',
                        'component_type': '框架梁',
                        'dimensions': {
                            'width': 0.3,
                            'height': 0.6,
                            'length': 6.0
                        },
                        'position': [50, 100],
                        'bbox': [30, 80, 120, 170],
                        'quantity': 1,
                        'reinforcement': {
                            'main': '6Φ22',
                            'stirrup': 'Φ8@150'
                        }
                    },
                    {
                        'component_id': 'KZ-1',
                        'component_type': '框架柱',
                        'dimensions': {
                            'width': 0.5,
                            'height': 0.5,
                            'length': 3.6
                        },
                        'position': [250, 300],  # 不同位置的相同构件
                        'bbox': [230, 280, 320, 370],
                        'quantity': 1
                    }
                ],
                'raw_text_summary': '识别到框架梁L-1和框架柱KZ-1'
            }
        }
    ]

def create_mock_slice_coordinate_map() -> Dict[str, Any]:
    """创建模拟的切片坐标映射表"""
    return {
        0: {
            'slice_id': 'slice_0_0',
            'offset_x': 0,
            'offset_y': 0,
            'slice_width': 400,
            'slice_height': 300
        },
        1: {
            'slice_id': 'slice_0_1',
            'offset_x': 0,
            'offset_y': 300,
            'slice_width': 400,
            'slice_height': 300
        }
    }

def create_mock_original_image_info() -> Dict[str, Any]:
    """创建模拟的原图信息"""
    return {
        'width': 800,
        'height': 600,
        'path': '/test/image.png'
    }

def test_ocr_merger():
    """测试OCR结果合并器"""
    print("=" * 60)
    print("🔄 测试OCR切片结果合并器")
    print("=" * 60)
    
    merger = ResultMergerService()
    
    # 准备测试数据
    slice_results = create_mock_ocr_slice_results()
    slice_coordinate_map = create_mock_slice_coordinate_map()
    original_image_info = create_mock_original_image_info()
    
    print(f"📊 输入数据:")
    print(f"  - 切片结果数量: {len(slice_results)}")
    print(f"  - 坐标映射数量: {len(slice_coordinate_map)}")
    print(f"  - 原图尺寸: {original_image_info['width']}x{original_image_info['height']}")
    
    # 执行合并
    result = merger.merge_ocr_slice_results(
        slice_results=slice_results,
        slice_coordinate_map=slice_coordinate_map,
        original_image_info=original_image_info,
        task_id="test_task_001",
        drawing_id=123
    )
    
    print(f"\n✅ 合并结果:")
    print(f"  - 成功状态: {result.get('success')}")
    
    if result.get('success'):
        ocr_full = result['ocr_full_result']
        print(f"  - 总切片数: {ocr_full['total_slices']}")
        print(f"  - 成功切片数: {ocr_full['successful_slices']}")
        print(f"  - 成功率: {ocr_full['success_rate']:.2%}")
        print(f"  - 合并后文本区域数: {ocr_full['total_text_regions']}")
        print(f"  - 总字符数: {ocr_full['total_characters']}")
        print(f"  - 平均置信度: {ocr_full['average_confidence']:.3f}")
        
        print(f"\n📝 合并后的完整文本:")
        print(f"  {repr(ocr_full['full_text_content'])}")
        
        print(f"\n🗺️ 文本区域详情:")
        for i, region in enumerate(ocr_full['all_text_regions'][:3]):  # 显示前3个
            bbox = region.get('bbox', [])
            text = region.get('text', '')
            slice_src = region.get('slice_source', {})
            print(f"  {i+1}. '{text}' @{bbox} (来源切片: {slice_src.get('slice_index')})")
        
        if len(ocr_full['all_text_regions']) > 3:
            print(f"  ... 还有 {len(ocr_full['all_text_regions']) - 3} 个文本区域")

def test_vision_merger():
    """测试Vision结果合并器"""
    print("\n" + "=" * 60)
    print("🔄 测试Vision分析结果合并器")
    print("=" * 60)
    
    merger = ResultMergerService()
    
    # 准备测试数据
    vision_results = create_mock_vision_slice_results()
    slice_coordinate_map = create_mock_slice_coordinate_map()
    original_image_info = create_mock_original_image_info()
    
    print(f"📊 输入数据:")
    print(f"  - Vision结果数量: {len(vision_results)}")
    total_components = sum(len(r['qto_data'].get('components', [])) for r in vision_results)
    print(f"  - 总构件数（合并前）: {total_components}")
    
    # 执行合并
    result = merger.merge_vision_analysis_results(
        vision_results=vision_results,
        slice_coordinate_map=slice_coordinate_map,
        original_image_info=original_image_info,
        task_id="test_task_001",
        drawing_id=123
    )
    
    print(f"\n✅ 合并结果:")
    print(f"  - 成功状态: {result.get('success')}")
    
    if result.get('success'):
        vision_full = result['vision_full_result']
        print(f"  - 总切片数: {vision_full['total_slices']}")
        print(f"  - 成功切片数: {vision_full['successful_slices']}")
        print(f"  - 合并后构件数: {vision_full['total_components']}")
        
        print(f"\n📋 项目信息:")
        project_info = vision_full['project_info']
        for key, value in project_info.items():
            if value:
                print(f"  - {key}: {value}")
        
        print(f"\n🏗️ 构件汇总:")
        component_summary = vision_full['component_summary']
        for comp_type, summary in component_summary.items():
            if isinstance(summary, dict):
                print(f"  - {comp_type}: {summary}")
        
        print(f"\n🔧 构件详情:")
        for i, component in enumerate(vision_full['merged_components']):
            comp_id = component.get('component_id', f'Component_{i+1}')
            comp_type = component.get('component_type', 'Unknown')
            quantity = component.get('quantity', 1)
            sources = len(component.get('slice_sources', []))
            print(f"  {i+1}. {comp_id} ({comp_type}) x{quantity} (来源: {sources}个切片)")
        
        print(f"\n📖 整合描述:")
        descriptions = vision_full['integrated_descriptions']
        for desc_type, content in descriptions.items():
            if content:
                print(f"  - {desc_type}: {content[:100]}...")

def test_coordinate_restoration():
    """测试坐标还原功能"""
    print("\n" + "=" * 60)
    print("🔄 测试坐标还原功能")
    print("=" * 60)
    
    merger = ResultMergerService()
    
    # 模拟切片中的文本区域（相对坐标）
    region = {
        'text': 'KZ-1',
        'bbox': [50, 100, 150, 130],
        'confidence': 0.9
    }
    
    # 切片信息
    slice_info = {
        'slice_id': 'slice_0_1',
        'offset_x': 200,
        'offset_y': 300
    }
    
    print(f"📍 原始区域: {region}")
    print(f"📍 切片偏移: x={slice_info['offset_x']}, y={slice_info['offset_y']}")
    
    # 执行坐标还原
    restored = merger._restore_text_coordinates(
        region, 
        slice_info['offset_x'], 
        slice_info['offset_y'], 
        slice_info, 
        0
    )
    
    print(f"📍 还原后区域: {restored}")
    print(f"📍 坐标变化: {region['bbox']} -> {restored['bbox']}")

def main():
    """主函数"""
    print("🚀 开始结果合并器功能测试")
    
    try:
        # 测试坐标还原
        test_coordinate_restoration()
        
        # 测试OCR合并
        test_ocr_merger()
        
        # 测试Vision合并
        test_vision_merger()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成!")
        print("=" * 60)
        
        print("\n📁 预期生成的文件:")
        print("  - ocr_results/123/ocr_full.json")
        print("  - llm_results/123/vision_full.json")
        
        print("\n📝 合并功能说明:")
        print("  1. OCR切片结果合并:")
        print("     - 坐标还原回原图坐标系")
        print("     - 去除重叠区域的重复文本")
        print("     - 按位置排序生成完整文本")
        print("     - 保存为 ocr_full.json")
        
        print("\n  2. Vision分析结果合并:")
        print("     - 项目信息选择最完整的一份")
        print("     - 构件按ID或坐标聚合去重")
        print("     - 坐标还原和属性融合")
        print("     - 图纸说明整合为长段文本")
        print("     - 保存为 vision_full.json")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 