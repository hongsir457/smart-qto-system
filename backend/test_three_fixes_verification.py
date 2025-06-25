#!/usr/bin/env python3
"""
三项关键修复验证脚本
1. 验证PaddleOCR文本纠错是否已禁用
2. 验证S3服务单例模式是否生效
3. 验证OCR文件名是否统一为merged_result.json
"""

import sys
import logging
from pathlib import Path

# 添加backend目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_1_paddleocr_text_correction_disabled():
    """测试1: 验证PaddleOCR文本纠错是否已禁用"""
    print("\n" + "="*60)
    print("测试1: 验证PaddleOCR文本纠错是否已禁用")
    print("="*60)
    
    try:
        # 读取paddle_ocr.py源码，检查文本纠错是否被注释
        paddle_ocr_file = Path(__file__).parent / "app" / "services" / "ocr" / "paddle_ocr.py"
        
        if not paddle_ocr_file.exists():
            print("❌ paddle_ocr.py 文件不存在")
            return False
            
        content = paddle_ocr_file.read_text(encoding='utf-8')
        
        # 检查是否包含被注释的纠错调用
        if "# processed_result = self._apply_construction_text_correction(processed_result)" in content:
            print("✅ 找到被注释的文本纠错调用")
            
            # 检查是否包含禁用日志
            if "logger.info(\"🚫 文本纠错已禁用，保持OCR原始结果\")" in content:
                print("✅ 找到文本纠错禁用日志")
                print("✅ 测试1通过：文本纠错已成功禁用")
                return True
            else:
                print("⚠️ 未找到禁用日志")
                return False
        else:
            print("❌ 未找到被注释的文本纠错调用")
            return False
            
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        return False

def test_2_s3_service_singleton():
    """测试2: 验证S3服务单例模式是否生效"""
    print("\n" + "="*60)
    print("测试2: 验证S3服务单例模式是否生效")
    print("="*60)
    
    try:
        from app.services.s3_service import S3Service
        
        # 创建多个S3Service实例
        service1 = S3Service()
        service2 = S3Service()
        service3 = S3Service()
        
        # 检查是否是同一个实例
        if service1 is service2 is service3:
            print("✅ S3Service实例化返回相同对象")
            
            # 检查是否有单例相关的属性
            if hasattr(S3Service, '_instance') and hasattr(S3Service, '_initialized'):
                print("✅ 找到单例模式相关属性")
                print("✅ 测试2通过：S3服务单例模式生效")
                return True
            else:
                print("⚠️ 未找到单例模式属性")
                return False
        else:
            print("❌ S3Service实例化返回不同对象")
            return False
            
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        return False

def test_3_ocr_filename_consistency():
    """测试3: 验证OCR文件名是否统一为merged_result.json"""
    print("\n" + "="*60)
    print("测试3: 验证OCR文件名是否统一为merged_result.json")
    print("="*60)
    
    try:
        # 检查PaddleOCR是否会保存固定名称的合并文件
        paddle_ocr_file = Path(__file__).parent / "app" / "services" / "ocr" / "paddle_ocr.py"
        
        if not paddle_ocr_file.exists():
            print("❌ paddle_ocr.py 文件不存在")
            return False
            
        content = paddle_ocr_file.read_text(encoding='utf-8')
        
        # 检查是否包含merged_result.json保存逻辑
        if 'f"ocr_results/{drawing_id}/merged_result.json"' in content:
            print("✅ 找到merged_result.json保存逻辑")
            
            # 检查是否有额外保存的注释
            if "修复核心问题" in content and "额外保存一个固定名称的合并文件" in content:
                print("✅ 找到额外保存固定名称文件的逻辑")
                
                # 检查返回值是否包含storage_result
                if '"storage_result": save_result_info.get("merged_result", {})' in content:
                    print("✅ 找到storage_result返回字段")
                    print("✅ 测试3通过：OCR文件名已统一为merged_result.json")
                    return True
                else:
                    print("⚠️ 未找到storage_result返回字段")
                    return False
            else:
                print("⚠️ 未找到额外保存逻辑")
                return False
        else:
            print("❌ 未找到merged_result.json保存逻辑")
            return False
            
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 开始三项关键修复验证...")
    print("修复项目:")
    print("1. 禁用PaddleOCR文本纠错")
    print("2. S3服务单例模式优化")
    print("3. OCR文件名统一为merged_result.json")
    
    # 执行所有测试
    test_results = []
    
    test_results.append(test_1_paddleocr_text_correction_disabled())
    test_results.append(test_2_s3_service_singleton())
    test_results.append(test_3_ocr_filename_consistency())
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"测试1 - PaddleOCR文本纠错禁用: {'✅ 通过' if test_results[0] else '❌ 失败'}")
    print(f"测试2 - S3服务单例模式: {'✅ 通过' if test_results[1] else '❌ 失败'}")
    print(f"测试3 - OCR文件名统一: {'✅ 通过' if test_results[2] else '❌ 失败'}")
    
    print(f"\n总体结果: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有修复验证成功！系统已准备就绪。")
        return True
    else:
        print("⚠️ 部分修复验证失败，请检查相关问题。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 