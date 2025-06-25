#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四步式网格切片分析系统测试脚本
演示完整的切片→分析→合并→还原流程
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
        logging.FileHandler('grid_slice_analysis_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_grid_slice_analysis():
    """测试网格切片分析系统"""
    
    logger.info("🚀 开始测试四步式网格切片分析系统")
    
    try:
        # 导入分析器
        from app.services.grid_slice_analyzer import GridSliceAnalyzer
        
        # 创建分析器实例
        analyzer = GridSliceAnalyzer(
            slice_size=1024,  # 1K切片
            overlap=128       # 128像素重叠
        )
        
        # 准备测试数据
        test_image = "test_images/sample_floorplan.png"
        if not os.path.exists(test_image):
            # 创建测试图像目录
            os.makedirs("test_images", exist_ok=True)
            logger.warning(f"⚠️ 测试图像不存在: {test_image}")
            logger.info("请将测试图纸放置在 test_images/sample_floorplan.png")
            return
        
        # 图纸基本信息
        drawing_info = {
            "scale": "1:100",
            "drawing_number": "S03",
            "page_number": 1,
            "project_name": "测试项目",
            "drawing_type": "结构图"
        }
        
        # 任务ID
        task_id = f"grid_test_{int(time.time())}"
        
        # 输出目录
        output_dir = f"temp_slices_{task_id}"
        
        logger.info(f"📐 测试参数:")
        logger.info(f"   - 图纸路径: {test_image}")
        logger.info(f"   - 切片大小: {analyzer.slice_size}x{analyzer.slice_size}")
        logger.info(f"   - 重叠区域: {analyzer.overlap}px")
        logger.info(f"   - 输出目录: {output_dir}")
        
        # 执行四步分析
        start_time = time.time()
        
        result = analyzer.analyze_drawing_with_grid_slicing(
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
            logger.info("✅ 四步网格切片分析完成！")
            
            # 输出分析结果统计
            qto_data = result["qto_data"]
            slice_metadata = result["slice_metadata"]
            
            logger.info(f"📊 分析结果统计:")
            logger.info(f"   - 总构件数: {qto_data['component_summary']['total_components']}")
            logger.info(f"   - 构件类型: {', '.join(qto_data['component_summary']['component_types'])}")
            logger.info(f"   - 切片总数: {len(slice_metadata['slice_info'])}")
            logger.info(f"   - 分析覆盖率: {qto_data['component_summary']['analysis_coverage']['coverage_ratio']:.1%}")
            
            # 输出合并统计
            merge_stats = slice_metadata.get("merge_statistics", {})
            if merge_stats:
                logger.info(f"🔀 合并统计:")
                logger.info(f"   - 原始构件: {merge_stats.get('original_count', 0)}")
                logger.info(f"   - 最终构件: {merge_stats.get('final_count', 0)}")
                logger.info(f"   - 合并率: {merge_stats.get('merge_ratio', 0):.1%}")
                logger.info(f"   - 重复构件: {merge_stats.get('exact_duplicates', 0)}")
                logger.info(f"   - 相似合并: {merge_stats.get('similar_merges', 0)}")
                logger.info(f"   - 跨切片合并: {merge_stats.get('cross_slice_merges', 0)}")
            
            # 输出前几个构件示例
            components = qto_data["components"]
            logger.info(f"📋 构件示例:")
            for i, comp in enumerate(components[:5]):
                logger.info(f"   {i+1}. {comp['id']} - {comp['type']} ({comp['size']}) "
                           f"- {comp['material']} - 切片{comp['source_block']}")
                
                if comp.get('global_coordinates'):
                    coords = comp['global_coordinates']
                    logger.info(f"      全局坐标: ({coords['x']}, {coords['y']}) "
                               f"{coords['width']}x{coords['height']}")
            
            # 保存完整结果
            result_file = f"grid_analysis_result_{task_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 完整结果已保存: {result_file}")
            
            # 输出可视化信息
            if slice_metadata.get("coordinate_restoration"):
                logger.info("🎨 坐标还原成功，已生成可视化图像")
                
        else:
            logger.error(f"❌ 分析失败: {result.get('error', '未知错误')}")
        
        # 演示分步测试
        logger.info("\n" + "="*60)
        logger.info("🔍 分步测试演示")
        test_individual_steps(analyzer, test_image, drawing_info, task_id)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_individual_steps(analyzer, test_image, drawing_info, task_id):
    """测试各个步骤"""
    
    try:
        # Step 1: 测试切片功能
        logger.info("📐 Step 1: 测试图纸切片...")
        output_dir = f"test_slices_{task_id}"
        
        slice_result = analyzer._slice_drawing_to_grid(
            test_image, output_dir, drawing_info
        )
        
        if slice_result["success"]:
            logger.info(f"✅ 切片成功: {slice_result['slice_count']} 个切片")
            logger.info(f"   网格大小: {slice_result['grid_size']}")
            
            # 显示前几个切片信息
            for i, slice_info in enumerate(analyzer.slices[:3]):
                logger.info(f"   切片 {i+1}: {slice_info.filename} "
                           f"位置({slice_info.x_offset},{slice_info.y_offset}) "
                           f"尺寸{slice_info.width}x{slice_info.height}")
        else:
            logger.error(f"❌ 切片失败: {slice_result.get('error')}")
            return
        
        # Step 2: 模拟分析（不调用真实AI）
        logger.info("🧠 Step 2: 模拟切片分析...")
        
        # 创建模拟构件数据
        from app.services.grid_slice_analyzer import ComponentInfo
        
        mock_components = []
        for i, slice_info in enumerate(analyzer.slices[:3]):  # 只测试前3个切片
            # 模拟每个切片识别到的构件
            slice_key = f"{slice_info.row}_{slice_info.col}"
            components = [
                ComponentInfo(
                    id=f"B{100+i}",
                    type="梁",
                    size="300x600",
                    material="C30",
                    location=f"轴线A-B/{i+1}-{i+2}",
                    source_block=slice_key,
                    confidence=0.9,
                    local_bbox={"x": 100, "y": 200, "width": 300, "height": 50}
                ),
                ComponentInfo(
                    id=f"KZ{i+1}",
                    type="柱",
                    size="400x400",
                    material="C30",
                    location=f"轴线{chr(65+i)}/{i+1}",
                    source_block=slice_key,
                    confidence=0.85,
                    local_bbox={"x": 200, "y": 300, "width": 40, "height": 40}
                )
            ]
            
            analyzer.slice_components[slice_key] = components
            mock_components.extend(components)
        
        logger.info(f"✅ 模拟分析完成: {len(mock_components)} 个构件")
        
        # Step 3: 测试合并逻辑
        logger.info("📚 Step 3: 测试构件合并...")
        
        merge_result = analyzer._merge_component_semantics()
        
        if merge_result["success"]:
            stats = merge_result["statistics"]
            logger.info(f"✅ 合并完成: {stats['original_count']} → {stats['final_count']}")
            logger.info(f"   合并率: {stats['merge_ratio']:.1%}")
        else:
            logger.error(f"❌ 合并失败: {merge_result.get('error')}")
            return
        
        # Step 4: 测试坐标还原
        logger.info("📎 Step 4: 测试坐标还原...")
        
        restore_result = analyzer._restore_global_coordinates(test_image)
        
        if restore_result["success"]:
            logger.info(f"✅ 坐标还原完成: {restore_result['restored_count']}/{restore_result['total_components']}")
            
            if restore_result.get("visualization", {}).get("success"):
                vis_path = restore_result["visualization"]["visualization_path"]
                logger.info(f"🎨 可视化图像: {vis_path}")
        else:
            logger.error(f"❌ 坐标还原失败: {restore_result.get('error')}")
        
        logger.info("✅ 分步测试完成")
        
    except Exception as e:
        logger.error(f"❌ 分步测试失败: {e}")

def demonstrate_merge_logic():
    """演示合并逻辑"""
    logger.info("\n" + "="*60)
    logger.info("🔀 演示智能合并逻辑")
    
    try:
        from app.services.grid_slice_analyzer import GridSliceAnalyzer, ComponentInfo
        
        analyzer = GridSliceAnalyzer()
        
        # 创建测试构件（模拟重复和相似情况）
        test_components = [
            # 完全重复的构件
            ComponentInfo("B101", "梁", "300x600", "C30", "轴线A-B/1-2", "0_0", 0.9),
            ComponentInfo("B101", "梁", "300x600", "C30", "轴线A-B/1-2", "0_1", 0.85),
            
            # 相似ID（OCR错误）
            ComponentInfo("KZ1", "柱", "400x400", "C30", "轴线A/1", "1_0", 0.9),
            ComponentInfo("KZ-1", "柱", "400x400", "C30", "轴线A/1", "1_1", 0.8),
            
            # 跨切片构件
            ComponentInfo("LB201", "板", "120", "C25", "楼板", "2_0", 0.9),
            ComponentInfo("LB202", "板", "120", "C25", "楼板", "2_1", 0.85),
            
            # 独立构件
            ComponentInfo("Q301", "墙", "200", "MU10", "轴线1/A-D", "3_0", 0.9),
        ]
        
        # 模拟设置
        analyzer.slice_components = {
            "0_0": [test_components[0]],
            "0_1": [test_components[1]],
            "1_0": [test_components[2]],
            "1_1": [test_components[3]],
            "2_0": [test_components[4]],
            "2_1": [test_components[5]],
            "3_0": [test_components[6]],
        }
        
        # 执行合并
        merge_result = analyzer._merge_component_semantics()
        
        if merge_result["success"]:
            logger.info("✅ 合并演示完成")
            
            stats = merge_result["statistics"]
            logger.info(f"📊 合并统计:")
            logger.info(f"   原始构件: {stats['original_count']}")
            logger.info(f"   最终构件: {stats['final_count']}")
            logger.info(f"   完全重复: {stats['exact_duplicates']}")
            logger.info(f"   相似合并: {stats['similar_merges']}")
            logger.info(f"   跨切片合并: {stats['cross_slice_merges']}")
            
            logger.info("🏗️ 合并后的构件:")
            for i, comp in enumerate(analyzer.merged_components):
                logger.info(f"   {i+1}. {comp.id} - {comp.type} "
                           f"来源切片: {comp.source_block} "
                           f"置信度: {comp.confidence:.2f}")
        else:
            logger.error(f"❌ 合并演示失败: {merge_result.get('error')}")
        
    except Exception as e:
        logger.error(f"❌ 合并逻辑演示失败: {e}")

if __name__ == "__main__":
    print("🏗️ 四步式网格切片分析系统测试")
    print("="*60)
    
    # 主测试
    test_grid_slice_analysis()
    
    # 合并逻辑演示
    demonstrate_merge_logic()
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    
    # 使用说明
    print("\n📖 使用说明:")
    print("1. 将测试图纸放置在 test_images/sample_floorplan.png")
    print("2. 确保AI分析器服务正常运行")
    print("3. 运行此脚本进行完整测试")
    print("\n推荐场景:")
    print("• 大尺寸建筑图纸（>4K分辨率）")
    print("• 复杂结构图纸（多构件类型）")
    print("• 需要精确坐标定位的项目")
    print("• 批量图纸处理任务") 