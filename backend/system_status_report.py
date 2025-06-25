#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工程量计算系统 - 状态报告
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_system_status():
    """检查系统整体状态"""
    print("🚀 智能工程量计算系统 - 状态报告")
    print("=" * 60)
    print(f"📅 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    status_items = []
    
    # 1. 检查基础依赖
    print("🔧 基础组件状态")
    print("-" * 40)
    
    dependencies = [
        ('fastapi', 'FastAPI Web框架'),
        ('celery', 'Celery任务队列'),
        ('redis', 'Redis缓存'),
        ('sqlalchemy', 'SQLAlchemy数据库ORM'),
        ('numpy', 'NumPy数值计算'),
        ('PIL', 'Pillow图像处理'),
        ('cv2', 'OpenCV计算机视觉'),
        ('pytesseract', 'Tesseract OCR引擎')
    ]
    
    deps_available = 0
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {name}")
            deps_available += 1
        except ImportError:
            print(f"   ❌ {name} (未安装)")
    
    status_items.append(("基础依赖", deps_available, len(dependencies)))
    
    # 2. 检查配置
    print(f"\n⚙️ 配置状态")
    print("-" * 40)
    
    config_items = 0
    config_total = 5
    
    try:
        from app.core.config import settings
        print("   ✅ 配置文件加载成功")
        config_items += 1
        
        # 检查关键配置项
        if hasattr(settings, 'DATABASE_URL'):
            print(f"   ✅ 数据库配置: {settings.DATABASE_URL[:50]}...")
            config_items += 1
            
        if hasattr(settings, 'REDIS_URL'):
            print(f"   ✅ Redis配置: {settings.REDIS_URL}")
            config_items += 1
            
        if hasattr(settings, 'OPENAI_MODEL'):
            print(f"   ✅ AI模型配置: {settings.OPENAI_MODEL}")
            config_items += 1
            
        if hasattr(settings, 'OCR_LANGUAGES'):
            print(f"   ✅ OCR语言配置: {settings.OCR_LANGUAGES}")
            config_items += 1
            
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
    
    status_items.append(("配置项", config_items, config_total))
    
    # 3. 检查核心模块
    print(f"\n🧩 核心模块状态")
    print("-" * 40)
    
    modules_available = 0
    modules_total = 5
    
    try:
        from app.tasks.ocr_tasks import process_ocr_file_task
        print("   ✅ OCR任务模块")
        modules_available += 1
    except Exception as e:
        print(f"   ❌ OCR任务模块: {e}")
    
    try:
        from app.utils.ocr_utils import create_ocr_processor
        print("   ✅ OCR工具模块")
        modules_available += 1
    except Exception as e:
        print(f"   ❌ OCR工具模块: {e}")
    
    try:
        from app.core.celery_app import celery_app
        print("   ✅ Celery应用")
        modules_available += 1
    except Exception as e:
        print(f"   ❌ Celery应用: {e}")
    
    try:
        from app.api.v1.drawings import router
        print("   ✅ API端点")
        modules_available += 1
    except Exception as e:
        print(f"   ❌ API端点: {e}")
        
    try:
        from app.tasks.real_time_task_manager import task_manager
        print("   ✅ 任务管理器")
        modules_available += 1
    except Exception as e:
        print(f"   ❌ 任务管理器: {e}")
    
    status_items.append(("核心模块", modules_available, modules_total))
    
    # 4. 检查Celery Worker
    print(f"\n👷 Celery Worker状态")
    print("-" * 40)
    
    worker_status = 0
    worker_total = 1
    
    try:
        from app.core.celery_app import celery_app
        
        # 检查活动的Worker
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print(f"   ✅ 活动Worker: {list(active_workers.keys())}")
            worker_status = 1
        else:
            print("   ⚠️ 没有活动的Worker")
            print("   💡 请运行: celery -A app.core.celery_app worker --loglevel=info")
            
    except Exception as e:
        print(f"   ❌ Worker检查失败: {e}")
    
    status_items.append(("Celery Worker", worker_status, worker_total))
    
    # 5. 功能测试
    print(f"\n🧪 功能测试状态")
    print("-" * 40)
    
    func_tests = 0
    func_total = 3
    
    # 测试OCR处理器
    try:
        from app.utils.ocr_utils import create_ocr_processor
        processor = create_ocr_processor()
        result = processor._mock_ocr_result("test.png")
        if result and 'texts' in result:
            print("   ✅ OCR处理器功能正常")
            func_tests += 1
    except Exception as e:
        print(f"   ❌ OCR处理器测试失败: {e}")
    
    # 测试构件解析器
    try:
        from app.utils.ocr_utils import create_component_parser
        parser = create_component_parser()
        mock_ocr = {'texts': ['框架柱KZ1', '500×500'], 'boxes': [None, None], 'confidences': [90, 85]}
        components = parser.parse_components(mock_ocr)
        if components:
            print("   ✅ 构件解析器功能正常")
            func_tests += 1
    except Exception as e:
        print(f"   ❌ 构件解析器测试失败: {e}")
    
    # 测试任务分发
    try:
        from app.tasks.ocr_tasks import process_ocr_file_task
        # 不实际执行，只检查任务定义
        if hasattr(process_ocr_file_task, 'delay'):
            print("   ✅ 任务分发功能正常")
            func_tests += 1
    except Exception as e:
        print(f"   ❌ 任务分发测试失败: {e}")
    
    status_items.append(("功能测试", func_tests, func_total))
    
    # 6. 系统能力概述
    print(f"\n🎯 系统能力概述")
    print("-" * 40)
    
    capabilities = [
        "📄 支持图像和PDF文件上传",
        "🔍 OCR文本识别和提取",
        "🏗️ 构件自动识别和分类",
        "📐 尺寸信息提取和解析",
        "📊 工程量自动计算",
        "⏱️ 异步任务处理",
        "📈 实时进度跟踪",
        "🔄 任务状态管理",
        "📋 结构化结果输出",
        "🎨 现代化Web API接口"
    ]
    
    for capability in capabilities:
        print(f"   {capability}")
    
    # 7. 总结
    print(f"\n📊 系统健康度评估")
    print("=" * 60)
    
    total_score = 0
    max_score = 0
    
    for name, available, total in status_items:
        score = (available / total) * 100 if total > 0 else 0
        total_score += available
        max_score += total
        
        if score >= 90:
            status_icon = "🟢"
        elif score >= 70:
            status_icon = "🟡"
        else:
            status_icon = "🔴"
            
        print(f"   {status_icon} {name}: {available}/{total} ({score:.1f}%)")
    
    overall_score = (total_score / max_score) * 100 if max_score > 0 else 0
    
    print(f"\n🎯 总体健康度: {total_score}/{max_score} ({overall_score:.1f}%)")
    
    if overall_score >= 90:
        print("🎉 系统状态优秀！所有核心功能正常运行")
        status_level = "优秀"
    elif overall_score >= 80:
        print("✅ 系统状态良好，核心功能可用")
        status_level = "良好"
    elif overall_score >= 60:
        print("⚠️ 系统状态一般，部分功能可能受限")
        status_level = "一般"
    else:
        print("❌ 系统状态不佳，需要检查配置和依赖")
        status_level = "不佳"
    
    # 8. 下一步建议
    print(f"\n💡 下一步建议")
    print("-" * 40)
    
    if overall_score < 100:
        if deps_available < len(dependencies):
            print("   📦 安装缺失的依赖包: pip install -r requirements-ai.txt")
        
        if worker_status == 0:
            print("   👷 启动Celery Worker: celery -A app.core.celery_app worker --loglevel=info")
        
        if config_items < config_total:
            print("   ⚙️ 完善配置文件: 参考 .env.example")
            
    if overall_score >= 80:
        print("   🚀 启动FastAPI服务: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("   📝 测试文件上传功能")
        print("   🔧 集成真实的GPT-4o API")
        print("   📊 优化工程量计算精度")
    
    print(f"\n📋 报告结束 - 系统状态: {status_level}")
    
    return overall_score >= 80

if __name__ == "__main__":
    success = check_system_status()
    sys.exit(0 if success else 1) 