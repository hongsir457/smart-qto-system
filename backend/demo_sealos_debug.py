#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sealos识别结果调试演示脚本
直接使用已知的S3键演示下载和查看功能
"""

import json
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_sealos_debug():
    """演示Sealos调试功能"""
    print("🚀 Sealos识别结果调试演示")
    print("=" * 50)
    
    # 初始化S3服务
    try:
        from app.services.s3_service import S3Service
        s3_service = S3Service()
        print("✅ S3服务初始化成功")
    except Exception as e:
        print(f"❌ S3服务初始化失败: {e}")
        return
    
    # 已知的S3键（来自刚才的测试）
    s3_key = "extraction_results/ef144f3f-2b92-4792-bd27-6bcbec9b2d41.json"
    
    print(f"\n📥 尝试从Sealos下载识别结果...")
    print(f"S3键: {s3_key}")
    
    # 创建下载目录
    download_dir = Path("debug_downloads")
    download_dir.mkdir(exist_ok=True)
    
    # 生成本地文件路径
    filename = Path(s3_key).name
    local_path = download_dir / filename
    
    # 下载文件
    try:
        success = s3_service.download_file(s3_key, str(local_path))
        
        if success:
            print(f"✅ 文件下载成功: {local_path}")
            
            # 分析下载的文件
            print(f"\n📊 分析识别结果...")
            analyze_result_file(str(local_path))
            
        else:
            print(f"❌ 文件下载失败")
            
    except Exception as e:
        print(f"❌ 下载异常: {e}")

def analyze_result_file(file_path: str):
    """分析识别结果文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n📄 文件分析: {Path(file_path).name}")
        print("=" * 50)
        
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
        print(f"  构件数量: {stats.get('total_components', 0)}")
        print(f"  源文本数量: {stats.get('source_texts', 0)}")
        print(f"  提取方法: {stats.get('extraction_method', 'N/A')}")
        print(f"  成功状态: {stats.get('success', False)}")
        
        # 构件详情
        components = data.get("components", [])
        print(f"\n🏗️ 识别的构件 ({len(components)} 个):")
        
        for i, comp in enumerate(components, 1):
            print(f"  {i}. {comp.get('name', '未知构件')}")
            print(f"     ├─ 编号: {comp.get('component_id', 'N/A')}")
            print(f"     ├─ 类型: {comp.get('component_type', 'N/A')}")
            print(f"     ├─ 尺寸: {comp.get('dimensions', 'N/A')}")
            print(f"     ├─ 材料: {comp.get('material', 'N/A')}")
            print(f"     ├─ 配筋: {comp.get('reinforcement', 'N/A')}")
            print(f"     ├─ 置信度: {comp.get('confidence', 0.0):.2f}")
            print(f"     └─ 来源: {comp.get('source', 'N/A')}")
            print()
        
        # 调试信息
        debug_info = data.get("debug_info", {})
        if debug_info:
            print(f"🔧 调试信息:")
            for key, value in debug_info.items():
                print(f"  - {key}: {value}")
        
        print(f"\n✅ 文件分析完成！")
        print(f"📁 本地文件路径: {file_path}")
        
    except Exception as e:
        print(f"❌ 文件分析失败: {e}")

def show_sealos_info():
    """显示Sealos存储信息"""
    print(f"\n🌐 Sealos存储信息:")
    print("=" * 50)
    
    # 显示配置信息
    import os
    from dotenv import load_dotenv
    load_dotenv('sealos_config.env')
    
    endpoint = os.getenv("S3_ENDPOINT", "未配置")
    bucket = os.getenv("S3_BUCKET", "未配置")
    
    print(f"📡 存储端点: {endpoint}")
    print(f"🪣 存储桶: {bucket}")
    print(f"📂 识别结果目录: extraction_results/")
    print(f"📄 文件命名格式: stage1_extraction_YYYYMMDD_HHMMSS_uuid.json")
    
    print(f"\n💡 使用说明:")
    print(f"  1. 每次构件识别都会自动保存结果到Sealos")
    print(f"  2. 文件包含完整的识别元数据和构件详情")
    print(f"  3. 可通过S3键直接下载查看历史结果")
    print(f"  4. 支持调试阶段的结果核对和验证")

if __name__ == "__main__":
    # 显示Sealos信息
    show_sealos_info()
    
    # 演示调试功能
    demo_sealos_debug() 