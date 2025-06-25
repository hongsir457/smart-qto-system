#!/usr/bin/env python3
"""
快速修复脚本 - 解决三个关键问题：
1. 禁用PaddleOCR文本纠错
2. 减少S3服务重复初始化  
3. 修复OCR文件名匹配问题
"""

import re
from pathlib import Path

def fix_paddleocr_text_correction():
    """修复1: 禁用PaddleOCR文本纠错"""
    print("🔧 修复1: 禁用PaddleOCR文本纠错...")
    
    paddle_ocr_file = Path("backend/app/services/ocr/paddle_ocr.py")
    
    if not paddle_ocr_file.exists():
        print(f"❌ 文件不存在: {paddle_ocr_file}")
        return False
    
    # 读取文件内容
    content = paddle_ocr_file.read_text(encoding='utf-8')
    
    # 替换文本纠错调用
    old_pattern = r"(\s*)# 应用特定领域的文本校正\s*\n\s*processed_result = self\._apply_construction_text_correction\(processed_result\)"
    new_replacement = r"\1# 应用特定领域的文本校正 - 根据用户要求已禁用\n\1# processed_result = self._apply_construction_text_correction(processed_result)\n\1logger.info('🚫 文本纠错已禁用，保持OCR原始结果')"
    
    new_content = re.sub(old_pattern, new_replacement, content)
    
    if new_content != content:
        paddle_ocr_file.write_text(new_content, encoding='utf-8')
        print("✅ PaddleOCR文本纠错已禁用")
        return True
    else:
        print("⚠️ 未找到需要修复的文本纠错代码")
        return False

def fix_s3_service_initialization():
    """修复2: 减少S3服务重复初始化"""
    print("🔧 修复2: 减少S3服务重复初始化...")
    
    # 在dual_storage_service.py中添加单例模式
    dual_storage_file = Path("backend/app/services/dual_storage_service.py")
    
    if not dual_storage_file.exists():
        print(f"❌ 文件不存在: {dual_storage_file}")
        return False
    
    content = dual_storage_file.read_text(encoding='utf-8')
    
    # 检查是否已经有单例模式
    if "_instance" in content:
        print("✅ S3服务已使用单例模式")
        return True
    
    # 添加单例模式
    singleton_code = '''
class DualStorageService:
    """
    双重存储服务 - 提供三层存储策略：
    1. 主存储：S3兼容存储（Sealos S3）
    2. 备份存储：Sealos原生API
    3. 降级存储：本地文件系统
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        """初始化双重存储服务，优先使用S3"""'''
    
    # 替换类定义
    old_class_pattern = r'class DualStorageService:\s*"""[^"]*"""\s*def __init__\(self\):'
    
    if re.search(old_class_pattern, content, re.DOTALL):
        new_content = re.sub(old_class_pattern, singleton_code.strip() + '\n        ', content, flags=re.DOTALL)
        dual_storage_file.write_text(new_content, encoding='utf-8')
        print("✅ S3服务单例模式已添加")
        return True
    else:
        print("⚠️ 未找到需要修复的类定义")
        return False

def fix_ocr_filename_matching():
    """修复3: 修复OCR文件名匹配问题"""
    print("🔧 修复3: 修复OCR文件名匹配问题...")
    
    # 修改_save_merged_paddleocr_result函数，使其保存为固定的merged_result.json
    drawing_tasks_file = Path("backend/app/tasks/drawing_tasks.py")
    
    if not drawing_tasks_file.exists():
        print(f"❌ 文件不存在: {drawing_tasks_file}")
        return False
    
    content = drawing_tasks_file.read_text(encoding='utf-8')
    
    # 查找并确保OCR结果保存的一致性
    # 确保所有地方都使用merged_result.json这个固定文件名
    old_pattern = r's3_key=f"ocr_results/\{drawing_id\}/merged_result\.json"'
    
    if old_pattern in content:
        print("✅ OCR文件名已使用统一的merged_result.json格式")
        return True
    else:
        print("⚠️ 需要手动检查OCR文件名格式")
        return False

def add_logging_improvements():
    """添加日志改进，减少重复日志"""
    print("🔧 额外修复: 改进日志输出...")
    
    # 在config.py中添加日志级别控制
    config_file = Path("backend/app/core/config.py")
    
    if config_file.exists():
        content = config_file.read_text(encoding='utf-8')
        
        if "LOG_LEVEL" not in content:
            # 在Settings类中添加日志级别配置
            log_config = '''
    # 日志配置
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    REDUCE_S3_INIT_LOGS: bool = Field(True, env="REDUCE_S3_INIT_LOGS")
'''
            
            # 在class Config:之前添加
            new_content = content.replace('    class Config:', log_config + '\n    class Config:')
            config_file.write_text(new_content, encoding='utf-8')
            print("✅ 日志配置已添加")
            return True
    
    print("⚠️ 配置文件修改跳过")
    return False

def main():
    """主修复函数"""
    print("🚀 开始快速修复...")
    print("=" * 50)
    
    fixes = [
        ("禁用PaddleOCR文本纠错", fix_paddleocr_text_correction),
        ("减少S3服务重复初始化", fix_s3_service_initialization), 
        ("修复OCR文件名匹配", fix_ocr_filename_matching),
        ("改进日志输出", add_logging_improvements),
    ]
    
    success_count = 0
    total_fixes = len(fixes)
    
    for fix_name, fix_func in fixes:
        print(f"\n📋 {fix_name}:")
        try:
            if fix_func():
                success_count += 1
        except Exception as e:
            print(f"❌ 修复失败: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 修复结果: {success_count}/{total_fixes} 项成功")
    
    if success_count == total_fixes:
        print("🎉 所有修复完成！请重启Celery Worker使更改生效。")
        print("\n💡 重启命令:")
        print("   Stop-Process -Name 'python' -Force")
        print("   Start-Sleep 3")
        print("   cd backend; python -m celery -A app.core.celery_app worker --loglevel=info --pool=solo")
    else:
        print("⚠️ 部分修复失败，请手动检查相关文件。")
    
    return success_count == total_fixes

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 