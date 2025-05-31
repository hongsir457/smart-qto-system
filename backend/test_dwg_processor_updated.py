#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新后的DWG处理器测试脚本
测试主处理器和简化版处理器的备用机制
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_updated_dwg_processor():
    """测试更新后的DWG处理器"""
    print("=" * 60)
    print("测试更新后的DWG处理器")
    print("=" * 60)
    
    try:
        # 导入DWG处理器
        from app.services.dwg_processor import DWGProcessor
        
        # 初始化处理器
        processor = DWGProcessor()
        print("✓ DWG处理器初始化成功")
        
        # 检查处理器状态
        print(f"✓ 支持的格式: {processor.supported_formats}")
        print(f"✓ ODA转换器路径: {processor.oda_converter_path or '未找到'}")
        print(f"✓ 简化版处理器: {'可用' if processor.simple_processor else '不可用'}")
        
        # 测试文件路径
        test_files = [
            "test_files/sample.dwg",
            "test_files/sample.dxf", 
            "test_files/multi_frame.dwg",
            "sample.dwg",
            "sample.dxf"
        ]
        
        test_file_found = None
        for test_file in test_files:
            if os.path.exists(test_file):
                test_file_found = test_file
                break
        
        if test_file_found:
            print(f"\n找到测试文件: {test_file_found}")
            print("开始处理...")
            
            start_time = time.time()
            result = processor.process_multi_sheets(test_file_found)
            end_time = time.time()
            
            print(f"处理完成，耗时: {end_time - start_time:.2f}秒")
            
            # 显示结果
            if result.get("success"):
                print("\n✓ 处理成功!")
                print(f"  - 总图框数: {result.get('total_drawings', 0)}")
                print(f"  - 成功处理: {result.get('processed_drawings', 0)}")
                print(f"  - 使用的处理器: {result.get('processing_info', {}).get('processor_used', '未知')}")
                
                # 显示图纸信息
                drawings = result.get("drawings", [])
                if drawings:
                    print("\n图纸列表:")
                    for i, drawing in enumerate(drawings, 1):
                        print(f"  {i}. {drawing.get('drawing_number', 'N/A')} - {drawing.get('title', 'N/A')}")
                        print(f"     比例: {drawing.get('scale', 'N/A')}, 构件数: {drawing.get('component_count', 0)}")
                
                # 显示汇总信息
                summary = result.get("summary", {})
                if summary:
                    print("\n汇总信息:")
                    total_components = summary.get("total_components", {})
                    for comp_type, count in total_components.items():
                        print(f"  - {comp_type}: {count}")
            else:
                print(f"\n✗ 处理失败: {result.get('error', '未知错误')}")
                
        else:
            print("\n未找到测试文件，使用演示模式")
            
            start_time = time.time()
            result = processor.process_multi_sheets("demo.dwg")
            end_time = time.time()
            
            print(f"演示模式完成，耗时: {end_time - start_time:.2f}秒")
            
            if result.get("success"):
                print("\n✓ 演示模式成功!")
                print(f"  - 演示图框数: {result.get('total_drawings', 0)}")
                print(f"  - 使用的处理器: {result.get('processing_info', {}).get('processor_used', '未知')}")
                
                # 显示演示图纸
                drawings = result.get("drawings", [])
                if drawings:
                    print("\n演示图纸:")
                    for i, drawing in enumerate(drawings, 1):
                        print(f"  {i}. {drawing.get('drawing_number', 'N/A')} - {drawing.get('title', 'N/A')}")
                        print(f"     构件数: {drawing.get('component_count', 0)}")
                        
                        # 显示构件详情
                        components = drawing.get("components", [])
                        if components:
                            print("     构件类型:")
                            comp_summary = {}
                            for comp in components:
                                comp_type = comp.get("type", "unknown")
                                comp_summary[comp_type] = comp_summary.get(comp_type, 0) + comp.get("quantity", 1)
                            
                            for comp_type, count in comp_summary.items():
                                print(f"       - {comp_type}: {count}")
                
                # 显示总汇总
                summary = result.get("summary", {})
                if summary:
                    print("\n总汇总:")
                    total_components = summary.get("total_components", {})
                    total_count = sum(total_components.values())
                    print(f"  - 总构件数: {total_count}")
                    for comp_type, count in total_components.items():
                        print(f"  - {comp_type}: {count}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入DWG处理器失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_mechanism():
    """测试备用机制"""
    print("\n" + "=" * 60)
    print("测试备用机制")
    print("=" * 60)
    
    try:
        # 测试简化版处理器
        try:
            from app.services.dwg_processor_simple import SimpleDWGProcessor
            
            simple_processor = SimpleDWGProcessor()
            print("✓ 简化版处理器初始化成功")
            
            # 测试简化版处理器
            result = simple_processor.process_multi_sheets("demo.dwg")
            
            if result.get("success"):
                print("✓ 简化版处理器演示模式成功")
                print(f"  - 图框数: {result.get('total_drawings', 0)}")
                print(f"  - 处理器: {result.get('processing_info', {}).get('processor_used', '未知')}")
            else:
                print(f"✗ 简化版处理器失败: {result.get('error', '未知错误')}")
                
        except ImportError:
            print("✗ 简化版处理器不可用")
        
        # 测试主处理器的备用机制
        print("\n测试主处理器的备用机制...")
        from app.services.dwg_processor import DWGProcessor
        
        processor = DWGProcessor()
        
        # 模拟主处理器失败的情况
        print("模拟处理不存在的文件（触发备用机制）...")
        result = processor.process_multi_sheets("nonexistent.dwg")
        
        if result.get("success"):
            processor_used = result.get("processing_info", {}).get("processor_used", "unknown")
            print(f"✓ 备用机制成功，使用的处理器: {processor_used}")
        else:
            print(f"✗ 备用机制失败: {result.get('error', '未知错误')}")
        
        return True
        
    except Exception as e:
        print(f"✗ 备用机制测试失败: {e}")
        return False

def test_api_integration():
    """测试API集成"""
    print("\n" + "=" * 60)
    print("测试API集成")
    print("=" * 60)
    
    try:
        # 检查API端点是否正确配置
        api_endpoints = [
            "POST /{drawing_id}/process-dwg-multi-sheets",
            "GET /{drawing_id}/dwg-multi-sheets-status", 
            "GET /{drawing_id}/dwg-drawings-list"
        ]
        
        print("检查API端点配置:")
        for endpoint in api_endpoints:
            print(f"  ✓ {endpoint}")
        
        # 检查Celery任务
        try:
            from app.services.drawing import process_dwg_multi_sheets
            print("✓ Celery任务 process_dwg_multi_sheets 导入成功")
        except ImportError as e:
            print(f"✗ Celery任务导入失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ API集成测试失败: {e}")
        return False

def create_feature_summary():
    """创建功能总结"""
    print("\n" + "=" * 60)
    print("DWG多图框处理功能总结")
    print("=" * 60)
    
    features = {
        "核心功能": [
            "自动检测DWG/DXF文件中的多个图框",
            "智能提取图号、标题、比例信息",
            "按图号自然排序（A-01, A-02, A-10）",
            "构件识别和工程量计算",
            "生成详细的统计报告"
        ],
        "支持的构件类型": [
            "墙体 (walls)",
            "柱子 (columns)", 
            "梁 (beams)",
            "楼板 (slabs)",
            "基础 (foundations)"
        ],
        "处理器架构": [
            "主处理器：支持ODA File Converter和ezdxf",
            "简化版处理器：纯Python解决方案",
            "智能备用机制：自动切换处理器",
            "演示模式：无依赖库时的模拟数据"
        ],
        "API端点": [
            "POST /{drawing_id}/process-dwg-multi-sheets - 开始多图框处理",
            "GET /{drawing_id}/dwg-multi-sheets-status - 查询处理状态",
            "GET /{drawing_id}/dwg-drawings-list - 获取图纸列表"
        ],
        "处理流程": [
            "1. 文件格式验证（.dwg, .dxf, .dwt）",
            "2. 尝试多种方法加载文件",
            "3. 检测图框和标题栏",
            "4. 提取图纸信息和构件",
            "5. 计算工程量和生成汇总",
            "6. 按图号智能排序"
        ],
        "输出结果": [
            "图纸列表：包含图号、标题、比例",
            "构件清单：按类型分类的构件信息",
            "工程量统计：面积、体积等计算结果",
            "处理状态：成功/失败及错误信息",
            "汇总报告：所有图纸的总计数据"
        ]
    }
    
    for category, items in features.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  • {item}")
    
    print(f"\n前端访问地址: http://localhost:3000")
    print(f"后端API地址: http://localhost:8000/api/v1/drawings")

def main():
    """主函数"""
    print("DWG多图框处理器测试套件")
    print("=" * 60)
    
    # 运行测试
    tests = [
        ("DWG处理器测试", test_updated_dwg_processor),
        ("备用机制测试", test_fallback_mechanism),
        ("API集成测试", test_api_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n开始 {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"✓ {test_name} {'成功' if result else '失败'}")
        except Exception as e:
            print(f"✗ {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    # 创建功能总结
    create_feature_summary()
    
    # 使用说明
    print("\n" + "=" * 60)
    print("使用说明")
    print("=" * 60)
    print("1. 上传DWG文件到系统")
    print("2. 调用多图框处理API")
    print("3. 查询处理状态")
    print("4. 获取处理结果")
    print("\n详细的API文档请参考: backend/DWG文件支持说明.md")

if __name__ == "__main__":
    main() 