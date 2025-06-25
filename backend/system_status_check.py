#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能工程量计算系统 - 后端状态检查脚本
"""

import sys
import os
from pathlib import Path
import importlib.util

# 添加项目根目录到Python路径
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))
os.environ['PYTHONPATH'] = str(backend_root)

def check_module_import(module_name, description):
    """检查模块是否可以正常导入"""
    try:
        if "." in module_name:
            # 处理相对导入
            parts = module_name.split(".")
            module = __import__(module_name, fromlist=[parts[-1]])
        else:
            module = __import__(module_name)
        print(f"✅ {description}: 导入成功")
        return True
    except Exception as e:
        print(f"❌ {description}: 导入失败 - {e}")
        return False

def check_fastapi_app():
    """检查FastAPI应用是否可以正常初始化"""
    try:
        from app.main import app
        print("✅ FastAPI应用: 初始化成功")
        return True
    except Exception as e:
        print(f"❌ FastAPI应用: 初始化失败 - {e}")
        return False

def check_database_models():
    """检查数据库模型"""
    models_to_check = [
        ("app.models.user", "用户模型"),
        ("app.models.drawing", "图纸模型"),
        ("app.models.task", "任务模型"),
    ]
    
    results = []
    for module_name, description in models_to_check:
        success = check_module_import(module_name, description)
        results.append(success)
    
    return all(results)

def check_api_endpoints():
    """检查API端点"""
    endpoints_to_check = [
        ("app.api.v1.endpoints.auth", "认证端点"),
        ("app.api.v1.drawings", "图纸端点"),
        ("app.api.v1.tasks", "任务端点"),
        ("app.api.v1.endpoints.chatgpt_analysis", "ChatGPT分析端点"),
        ("app.api.v1.endpoints.playground", "测试环境端点"),
    ]
    
    results = []
    for module_name, description in endpoints_to_check:
        success = check_module_import(module_name, description)
        results.append(success)
    
    return all(results)

def check_services():
    """检查核心服务模块"""
    services_to_check = [
        ("app.services.auth", "认证服务"),
        ("app.services.storage", "存储服务"),
        ("app.services.export", "导出服务"),
        ("app.crud.users", "用户CRUD"),
        ("app.crud.drawings", "图纸CRUD"),
    ]
    
    results = []
    for module_name, description in services_to_check:
        success = check_module_import(module_name, description)
        results.append(success)
    
    return all(results)

def check_configuration():
    """检查配置"""
    try:
        from app.core.config import settings
        print("✅ 配置系统: 加载成功")
        print(f"   - 项目名称: {settings.PROJECT_NAME}")
        print(f"   - API版本: {settings.API_V1_STR}")
        print(f"   - 调试模式: {settings.DEBUG}")
        return True
    except Exception as e:
        print(f"❌ 配置系统: 加载失败 - {e}")
        return False

def check_ai_services():
    """检查AI相关服务（简化检查）"""
    print("\n🤖 AI服务状态检查:")
    
    # 检查OCR相关组件
    try:
        from app.services.ocr.paddle_ocr import PaddleOCRService
        print("✅ PaddleOCR服务: 可导入")
    except Exception as e:
        print(f"⚠️ PaddleOCR服务: 导入失败 - {e}")
    
    # 检查LLM服务
    try:
        from app.services.llm.openai_service import OpenAIService
        print("✅ OpenAI服务: 可导入")
    except Exception as e:
        print(f"⚠️ OpenAI服务: 导入失败 - {e}")
    
    # 检查YOLO服务
    try:
        from app.services.ai.yolo_detector import YOLODetector
        print("✅ YOLO检测器: 可导入")
    except Exception as e:
        print(f"⚠️ YOLO检测器: 导入失败 - {e}")

def check_file_structure():
    """检查关键文件结构"""
    critical_files = [
        "app/main.py",
        "app/core/config.py",
        "app/database.py",
        "app/api/v1/api.py",
        "requirements.txt",
    ]
    
    missing_files = []
    for file_path in critical_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 文件结构: 缺少关键文件 {missing_files}")
        return False
    else:
        print("✅ 文件结构: 完整")
        return True

def main():
    """主检查函数"""
    print("🔍 智能工程量计算系统 - 后端状态检查")
    print("=" * 50)
    
    checks = [
        ("文件结构", check_file_structure),
        ("配置系统", check_configuration),
        ("数据库模型", check_database_models),
        ("API端点", check_api_endpoints),
        ("核心服务", check_services),
        ("FastAPI应用", check_fastapi_app),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 检查: {check_name}")
        print("-" * 30)
        success = check_func()
        results.append((check_name, success))
    
    # AI服务检查（单独处理，不影响总体结果）
    check_ai_services()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 系统状态总结:")
    passed = 0
    for check_name, success in results:
        status = "✅ 正常" if success else "❌ 异常"
        print(f"  {check_name}: {status}")
        if success:
            passed += 1
    
    total = len(results)
    print(f"\n核心系统状态: {passed}/{total} 正常")
    
    if passed == total:
        print("🎉 后端系统基础功能完整，可以启动！")
        print("\n💡 启动建议:")
        print("   1. 运行: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("   2. 访问API文档: http://localhost:8000/docs")
        print("   3. 健康检查: http://localhost:8000/health")
        return 0
    else:
        print("⚠️ 后端系统存在问题，建议修复后再启动")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 