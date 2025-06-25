#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sealos识别结果调试查看工具
用于查看和下载保存在Sealos上的一阶段识别结果
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_sealos_config():
    """加载Sealos配置"""
    from dotenv import load_dotenv
    load_dotenv('sealos_config.env')
    
    config = {
        "S3_ENDPOINT": os.getenv("S3_ENDPOINT"),
        "S3_ACCESS_KEY": os.getenv("S3_ACCESS_KEY"),
        "S3_SECRET_KEY": os.getenv("S3_SECRET_KEY"),
        "S3_BUCKET": os.getenv("S3_BUCKET"),
        "S3_REGION": os.getenv("S3_REGION", "us-east-1")
    }
    
    return config

def init_s3_service():
    """初始化S3服务"""
    try:
        from app.services.s3_service import S3Service
        s3_service = S3Service()
        logger.info("✅ S3服务初始化成功")
        return s3_service
    except Exception as e:
        logger.error(f"❌ S3服务初始化失败: {e}")
        return None

def download_extraction_result(s3_service, s3_key: str, local_dir: str = "debug_downloads"):
    """
    从Sealos下载识别结果文件
    
    Args:
        s3_service: S3服务实例
        s3_key: S3文件键
        local_dir: 本地下载目录
    """
    try:
        # 确保下载目录存在
        Path(local_dir).mkdir(exist_ok=True)
        
        # 提取文件名
        filename = Path(s3_key).name
        local_path = Path(local_dir) / filename
        
        # 下载文件
        success = s3_service.download_file(s3_key, str(local_path))
        
        if success:
            logger.info(f"✅ 文件下载成功: {local_path}")
            return str(local_path)
        else:
            logger.error(f"❌ 文件下载失败: {s3_key}")
            return None
            
    except Exception as e:
        logger.error(f"❌ 下载异常: {e}")
        return None

def analyze_extraction_result(file_path: str):
    """
    分析下载的识别结果文件
    
    Args:
        file_path: 本地文件路径
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📄 分析文件: {Path(file_path).name}")
        print("=" * 60)
        
        # 元信息
        meta = data.get("meta", {})
        print(f"🆔 识别ID: {meta.get('extraction_id', 'N/A')}")
        print(f"⏰ 识别时间: {meta.get('extraction_time', 'N/A')}")
        print(f"🎯 阶段: {meta.get('stage', 'N/A')}")
        print(f"🤖 AI模型: {meta.get('ai_model', 'N/A')}")
        print(f"🖼️ 源图片: {meta.get('source_image', 'N/A')}")
        
        # 统计信息
        stats = data.get("statistics", {})
        print(f"\n📊 统计信息:")
        print(f"  - 识别构件数量: {stats.get('total_components', 0)}")
        print(f"  - 源文本数量: {stats.get('source_texts', 0)}")
        print(f"  - 提取方法: {stats.get('extraction_method', 'N/A')}")
        print(f"  - 是否成功: {stats.get('success', False)}")
        
        # 构件详情
        components = data.get("components", [])
        print(f"\n🏗️ 构件详情 ({len(components)} 个):")
        
        for i, comp in enumerate(components, 1):
            print(f"  {i}. {comp.get('name', '未知构件')}")
            print(f"     编号: {comp.get('component_id', 'N/A')}")
            print(f"     类型: {comp.get('component_type', 'N/A')}")
            print(f"     尺寸: {comp.get('dimensions', 'N/A')}")
            print(f"     材料: {comp.get('material', 'N/A')}")
            print(f"     配筋: {comp.get('reinforcement', 'N/A')}")
            print(f"     置信度: {comp.get('confidence', 0.0):.2f}")
            print(f"     来源: {comp.get('source', 'N/A')}")
            print()
        
        # 调试信息
        debug_info = data.get("debug_info", {})
        if debug_info:
            print(f"🔧 调试信息:")
            for key, value in debug_info.items():
                print(f"  - {key}: {value}")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ 文件分析失败: {e}")
        return None

def analyze_ocr_result(file_path: str):
    """
    分析下载的OCR原始结果文件
    
    Args:
        file_path: 本地文件路径
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📖 OCR结果分析: {Path(file_path).name}")
        print("=" * 60)
        
        # 元信息
        meta = data.get("meta", {})
        print(f"🆔 OCR ID: {meta.get('ocr_id', 'N/A')}")
        print(f"⏰ 识别时间: {meta.get('ocr_time', 'N/A')}")
        print(f"🎯 阶段: {meta.get('stage', 'N/A')}")
        print(f"🤖 OCR引擎: {meta.get('ocr_engine', 'N/A')}")
        print(f"🖼️ 源图片: {meta.get('source_image', 'N/A')}")
        
        # 处理信息
        processing = data.get("processing_info", {})
        print(f"\n⚙️ 处理信息:")
        print(f"  状态: {processing.get('status', 'N/A')}")
        print(f"  文本数量: {processing.get('total_texts', 0)}")
        print(f"  处理时间: {processing.get('processing_time', 0.0)}秒")
        print(f"  模拟模式: {processing.get('mock_mode', False)}")
        print(f"  引擎状态: {processing.get('engine_status', 'N/A')}")
        
        # 摘要信息
        summary = data.get("summary", {})
        print(f"\n📊 摘要统计:")
        print(f"  文本总数: {summary.get('text_count', 0)}")
        print(f"  高置信度文本: {summary.get('high_confidence_count', 0)}")
        print(f"  平均置信度: {summary.get('average_confidence', 0.0):.3f}")
        print(f"  所有文本: {summary.get('all_text', 'N/A')}")
        
        # 原始文本详情
        raw_texts = data.get("raw_texts", [])
        print(f"\n📝 识别文本详情 ({len(raw_texts)} 个):")
        
        for i, text_item in enumerate(raw_texts, 1):
            bbox = text_item.get("bbox", {})
            print(f"  {i}. \"{text_item.get('text', 'N/A')}\"")
            print(f"     ├─ 置信度: {text_item.get('confidence', 0.0):.3f}")
            print(f"     ├─ 位置: ({bbox.get('center_x', 0):.0f}, {bbox.get('center_y', 0):.0f})")
            print(f"     ├─ 尺寸: {bbox.get('width', 0):.0f}×{bbox.get('height', 0):.0f}")
            print(f"     └─ 面积: {text_item.get('bbox_area', 0.0):.0f}像素²")
            print()
        
        # 边界框分析
        debug_info = data.get("debug_info", {})
        bbox_analysis = debug_info.get("bbox_analysis", {})
        if bbox_analysis:
            print(f"🔧 边界框分析:")
            print(f"  边界框数量: {bbox_analysis.get('bbox_count', 0)}")
            print(f"  总面积: {bbox_analysis.get('total_area', 0.0):.0f}像素²")
            print(f"  平均面积: {bbox_analysis.get('average_area', 0.0):.0f}像素²")
            print(f"  最大面积: {bbox_analysis.get('max_area', 0.0):.0f}像素²")
            print(f"  最小面积: {bbox_analysis.get('min_area', 0.0):.0f}像素²")
            print(f"  平均文本长度: {bbox_analysis.get('average_text_length', 0.0):.1f}字符")
            print(f"  最长文本: {bbox_analysis.get('longest_text', 0)}字符")
        
        print(f"\n✅ OCR结果分析完成！")
        print(f"📁 本地文件路径: {file_path}")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ OCR结果分析失败: {e}")
        return None

def view_recent_extraction_results(s3_service, limit: int = 5):
    """
    查看最近的识别结果（模拟功能）
    
    Args:
        s3_service: S3服务实例
        limit: 显示数量限制
    """
    print(f"\n🔍 查看最近 {limit} 个识别结果:")
    print("=" * 60)
    
    # 构件提取结果示例
    extraction_sample_keys = [
        "extraction_results/ef144f3f-2b92-4792-bd27-6bcbec9b2d41.json"
    ]
    
    # OCR原始结果示例
    ocr_sample_keys = [
        "ocr_results/e36e0ccc-489e-42a2-804d-328e58f74b84.json"
    ]
    
    print("💡 手动查看识别结果:")
    print("请将已知的S3键添加到下面的列表中进行查看")
    
    print(f"\n🏗️ 构件提取结果:")
    for i, key in enumerate(extraction_sample_keys, 1):
        print(f"   📄 结果 {i}: {key}")
        
        # 尝试下载并分析
        local_file = download_extraction_result(s3_service, key)
        if local_file:
            analyze_extraction_result(local_file)
    
    print(f"\n📖 OCR原始结果:")
    for i, key in enumerate(ocr_sample_keys, 1):
        print(f"   📄 结果 {i}: {key}")
        
        # 尝试下载并分析
        local_file = download_extraction_result(s3_service, key)
        if local_file:
            analyze_ocr_result(local_file)

def interactive_debug_menu(s3_service):
    """交互式调试菜单"""
    while True:
        print("\n" + "=" * 60)
        print("🔧 Sealos识别结果调试工具")
        print("=" * 60)
        print("1. 查看最近识别结果")
        print("2. 下载指定S3键的结果")
        print("3. 分析本地结果文件")
        print("4. 分析OCR原始结果文件")
        print("5. 显示Sealos配置")
        print("0. 退出")
        print("=" * 60)
        
        choice = input("请选择操作 (0-5): ").strip()
        
        if choice == "0":
            print("👋 退出调试工具")
            break
        elif choice == "1":
            view_recent_extraction_results(s3_service)
        elif choice == "2":
            s3_key = input("请输入S3键: ").strip()
            if s3_key:
                local_file = download_extraction_result(s3_service, s3_key)
                if local_file:
                    analyze_extraction_result(local_file)
        elif choice == "3":
            file_path = input("请输入本地文件路径: ").strip()
            if file_path and Path(file_path).exists():
                analyze_extraction_result(file_path)
            else:
                print("❌ 文件不存在")
        elif choice == "4":
            file_path = input("请输入OCR结果文件路径: ").strip()
            if file_path and Path(file_path).exists():
                analyze_ocr_result(file_path)
            else:
                print("❌ 文件不存在")
        elif choice == "5":
            config = load_sealos_config()
            print("\n🔧 Sealos配置:")
            for key, value in config.items():
                if "KEY" in key and value:
                    # 隐藏敏感信息
                    display_value = value[:8] + "***" if len(value) > 8 else "***"
                else:
                    display_value = value
                print(f"  {key}: {display_value}")
        else:
            print("❌ 无效选择")

def main():
    """主函数"""
    print("🚀 启动Sealos识别结果调试工具")
    
    # 初始化S3服务
    s3_service = init_s3_service()
    if not s3_service:
        print("❌ S3服务初始化失败，请检查配置")
        return
    
    # 启动交互式菜单
    interactive_debug_menu(s3_service)

if __name__ == "__main__":
    main() 