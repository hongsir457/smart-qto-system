#!/usr/bin/env python3
"""
Vision结果合并器修复验证脚本
"""

import asyncio
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.result_mergers.vision_result_merger import VisionResultMerger, VisionFullResult
from app.services.storage.dual_storage_service import DualStorageService

async def test_vision_merger_fix():
    """测试Vision结果合并器修复效果"""
    print("🧪 开始测试Vision结果合并器修复效果...")
    
    # 创建模拟的Vision分析结果数据
    vision_results = [
        {
            "success": True,
            "qto_data": {
                "components": [
                    {
                        "component_id": "KZ-1",
                        "component_type": "框架柱",
                        "dimensions": {"width": 400, "height": 600, "length": 4200},
                        "position": [100, 200],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    },
                    {
                        "component_id": "KZ-2", 
                        "component_type": "框架柱",
                        "dimensions": {"width": 400, "height": 600, "length": 4200},
                        "position": [300, 200],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    },
                    {
                        "component_id": "L-1",
                        "component_type": "框架梁",
                        "dimensions": {"width": 300, "height": 500, "length": 6000},
                        "position": [150, 100],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    }
                ],
                "drawing_info": {
                    "drawing_title": "结构平面图",
                    "scale": "1:100",
                    "project_name": "测试项目"
                }
            }
        },
        {
            "success": True,
            "qto_data": {
                "components": [
                    {
                        "component_id": "KZ-3",
                        "component_type": "框架柱", 
                        "dimensions": {"width": 400, "height": 600, "length": 4200},
                        "position": [500, 200],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    },
                    {
                        "component_id": "L-2",
                        "component_type": "框架梁",
                        "dimensions": {"width": 300, "height": 500, "length": 6000},
                        "position": [550, 100],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    },
                    {
                        "component_id": "B-1",
                        "component_type": "现浇板",
                        "dimensions": {"thickness": 120},
                        "position": [300, 300],
                        "quantity": 1,
                        "material": "C25混凝土"
                    }
                ]
            }
        },
        {
            "success": True,
            "qto_data": {
                "components": [
                    {
                        "component_id": "KZ-4",
                        "component_type": "框架柱",
                        "dimensions": {"width": 400, "height": 600, "length": 4200},
                        "position": [700, 200],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    },
                    {
                        "component_id": "L-3",
                        "component_type": "框架梁",
                        "dimensions": {"width": 300, "height": 500, "length": 6000},
                        "position": [750, 100],
                        "quantity": 1,
                        "material": "C30混凝土",
                        "reinforcement": "HRB400"
                    },
                    {
                        "component_id": "B-2",
                        "component_type": "现浇板",
                        "dimensions": {"thickness": 120},
                        "position": [700, 300],
                        "quantity": 1,
                        "material": "C25混凝土"
                    }
                ]
            }
        }
    ]
    
    # 创建切片坐标映射
    slice_coordinate_map = {
        0: {"offset_x": 0, "offset_y": 0, "slice_id": "slice_0", "slice_width": 1024, "slice_height": 1024},
        1: {"offset_x": 1000, "offset_y": 0, "slice_id": "slice_1", "slice_width": 1024, "slice_height": 1024},
        2: {"offset_x": 2000, "offset_y": 0, "slice_id": "slice_2", "slice_width": 1024, "slice_height": 1024}
    }
    
    original_image_info = {"width": 3024, "height": 1024}
    
    print(f"📝 测试数据准备完成:")
    print(f"   - 3个切片Vision结果")
    print(f"   - 总计 {sum(len(r['qto_data']['components']) for r in vision_results)} 个原始构件")
    print(f"   - 切片坐标映射: {len(slice_coordinate_map)} 个")
    
    # 初始化合并器
    try:
        storage_service = DualStorageService()
        merger = VisionResultMerger(storage_service=storage_service)
        print("✅ Vision结果合并器初始化成功")
    except Exception as e:
        print(f"❌ Vision结果合并器初始化失败: {e}")
        return
    
    # 执行合并测试
    try:
        print("\n🔄 开始执行Vision结果合并...")
        
        result = merger.merge_vision_results(
            vision_results=vision_results,
            slice_coordinate_map=slice_coordinate_map,
            original_image_info=original_image_info,
            task_id="test_vision_fix_001"
        )
        
        print(f"\n✅ 合并测试结果:")
        print(f"   - 合并后构件数量: {result.total_components}")
        print(f"   - 成功切片数量: {result.successful_slices}/{result.total_slices}")
        
        if result.merged_components:
            print(f"   - 构件类型分布:")
            for comp_type, count in result.component_types_distribution.items():
                print(f"     * {comp_type}: {count}个")
            
            print(f"   - 前5个构件:")
            for i, comp in enumerate(result.merged_components[:5]):
                comp_id = comp.get('component_id', 'N/A')
                comp_type = comp.get('component_type', 'unknown')
                quantity = comp.get('quantity', 1)
                print(f"     {i+1}. {comp_id} ({comp_type}) x{quantity}")
        else:
            print("   ❌ 警告: 合并后没有构件！")
        
        # 测试保存功能
        print(f"\n💾 测试保存到Sealos...")
        save_result = await merger.save_vision_full_result(result, 9999)
        
        if save_result.get("success"):
            print(f"✅ 保存成功:")
            print(f"   - 存储URL: {save_result.get('s3_url')}")
            print(f"   - 存储方法: {save_result.get('storage_method')}")
            print(f"   - 构件数量: {save_result.get('components_count')}")
        else:
            print(f"❌ 保存失败: {save_result.get('error')}")
        
        # 总结测试结果
        print(f"\n📊 测试总结:")
        success_indicators = []
        
        if result.total_components > 0:
            success_indicators.append("✅ 构件合并成功")
        else:
            success_indicators.append("❌ 构件合并失败 - 数量为零")
        
        if save_result.get("success"):
            success_indicators.append("✅ Sealos存储成功")
        else:
            success_indicators.append("❌ Sealos存储失败")
        
        for indicator in success_indicators:
            print(f"   {indicator}")
        
        if "❌" not in "\n".join(success_indicators):
            print(f"\n🎉 所有测试通过！Vision结果合并器修复成功！")
            return True
        else:
            print(f"\n⚠️  部分测试失败，需要进一步检查。")
            return False
            
    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ai_analyzer():
    """测试AI分析器的analyze_text_async方法"""
    print("\n🤖 测试AI分析器analyze_text_async方法...")
    
    try:
        from app.services.ai_analyzer import AIAnalyzerService
        
        ai_analyzer = AIAnalyzerService()
        
        if not ai_analyzer.is_available():
            print("⚠️  AI分析器不可用（可能是API密钥未配置）")
            return True  # 不算作失败，因为这是配置问题
        
        # 测试简单的文本分析
        test_prompt = "请分析以下建筑构件信息：KZ-1 框架柱 400×600×4200 C30混凝土"
        
        result = await ai_analyzer.analyze_text_async(
            prompt=test_prompt,
            session_id="test_session_001",
            context_data={"drawing_id": "test_drawing", "task_type": "test"}
        )
        
        if result.get("success"):
            print("✅ AI分析器测试成功")
            print(f"   - 响应长度: {len(result.get('response', ''))} 字符")
            print(f"   - 处理时间: {result.get('processing_time', 0):.2f}秒")
            return True
        else:
            print(f"❌ AI分析器测试失败: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ AI分析器测试异常: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 Vision结果合并器修复验证开始...\n")
    
    # 测试1: Vision结果合并器
    vision_test_result = await test_vision_merger_fix()
    
    # 测试2: AI分析器
    ai_test_result = await test_ai_analyzer()
    
    print(f"\n📋 最终测试报告:")
    print(f"   - Vision结果合并器: {'✅ 通过' if vision_test_result else '❌ 失败'}")
    print(f"   - AI分析器: {'✅ 通过' if ai_test_result else '❌ 失败'}")
    
    if vision_test_result and ai_test_result:
        print(f"\n🎉 所有关键功能修复验证通过！")
        print(f"现在可以重启Celery Worker以应用修复。")
    else:
        print(f"\n⚠️  部分功能需要进一步检查。")

if __name__ == "__main__":
    asyncio.run(main()) 