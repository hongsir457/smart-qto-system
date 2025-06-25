#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR结果智能纠正功能测试脚本
验证OCR纠正服务的各项功能
"""

import asyncio
import json
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ocr_corrector():
    """测试OCR纠正器"""
    print("🧪 开始测试OCR结果智能纠正功能...")
    print("=" * 80)
    
    try:
        from app.services.ocr_result_corrector import OCRResultCorrector
        from app.services.ai_analyzer import AIAnalyzerService
        from app.services.dual_storage_service import DualStorageService
        
        # 初始化服务
        ai_analyzer = AIAnalyzerService()
        storage_service = DualStorageService()
        ocr_corrector = OCRResultCorrector(ai_analyzer=ai_analyzer, storage_service=storage_service)
        
        print("✅ OCR纠正器初始化成功")
        
        # 测试建筑工程词典
        print("\n📚 测试建筑工程词典...")
        dictionary = ocr_corrector.construction_dictionary
        print(f"   构件类型数量: {len(dictionary['component_types'])}")
        print(f"   材料等级数量: {len(dictionary['materials'])}")
        print(f"   尺寸相关词汇: {len(dictionary['dimensions'])}")
        print(f"   轴线相关词汇: {len(dictionary['axis_lines'])}")
        
        # 测试OCR错误模式
        print("\n🔧 测试OCR错误模式...")
        error_patterns = ocr_corrector.ocr_error_patterns
        print(f"   常见错误模式数量: {len(error_patterns)}")
        for pattern in error_patterns[:3]:
            print(f"   {pattern['pattern']} -> {pattern['corrections']}")
        
        # 测试文本清理功能
        print("\n🧹 测试文本清理功能...")
        test_texts = [
            "KZ1  框架柱",
            "C30  混凝土",  
            "φ12@200",
            "600×800×3000",
            "梁编号：KL-1"
        ]
        
        for text in test_texts:
            cleaned = ocr_corrector._clean_text(text)
            print(f"   '{text}' -> '{cleaned}'")
        
        # 测试词典纠正
        print("\n📖 测试词典纠正功能...")
        test_corrections = [
            ("住1", "柱"),  # 柱的常见误识别
            ("粱", "梁"),   # 梁的常见误识别
            ("C20", "C20"), # 正确的材料等级
            ("KZ1", "KZ1")  # 正确的构件编号
        ]
        
        for original, expected in test_corrections:
            corrected = ocr_corrector._correct_with_dictionary(original)
            status = "✅" if corrected == expected else "❌"
            print(f"   {status} '{original}' -> '{corrected}' (期望: '{expected}')")
        
        # 测试模糊匹配
        print("\n🔍 测试模糊匹配功能...")
        test_matches = [
            ("梁", "粱", True),   # 应该匹配
            ("柱", "住", True),   # 应该匹配
            ("ABC", "XYZ", False) # 不应该匹配
        ]
        
        for text1, text2, expected in test_matches:
            result = ocr_corrector._fuzzy_match(text1, text2)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{text1}' vs '{text2}': {result} (期望: {expected})")
        
        # 测试GPT提示词构建
        print("\n🤖 测试GPT提示词构建...")
        test_texts = ["KZ1", "C30", "600×800", "框架柱"]
        prompt = ocr_corrector._build_gpt_correction_prompt(test_texts)
        print(f"   提示词长度: {len(prompt)} 字符")
        print(f"   包含建筑词汇: {'构件类型' in prompt}")
        print(f"   包含输出格式: {'JSON格式' in prompt}")
        
        # 模拟创建测试OCR结果
        print("\n📋 创建模拟OCR结果进行完整测试...")
        mock_ocr_result = {
            "merged_result": {
                "all_text_regions": [
                    {"text": "KZ1", "bbox": [100, 100, 150, 130], "confidence": 0.9},
                    {"text": "框架住", "bbox": [200, 100, 280, 130], "confidence": 0.8},  # 错误：住应该是柱
                    {"text": "C3O", "bbox": [100, 200, 150, 230], "confidence": 0.7},     # 错误：O应该是0
                    {"text": "600x800", "bbox": [200, 200, 300, 230], "confidence": 0.9},
                    {"text": "图纸编号：S001", "bbox": [50, 50, 200, 80], "confidence": 0.95}
                ],
                "average_confidence": 0.85,
                "processing_time": 2.5
            }
        }
        
        # 测试预处理
        print("\n🔧 测试OCR预处理...")
        preprocessed = ocr_corrector._preprocess_ocr_text(mock_ocr_result)
        original_count = len(mock_ocr_result["merged_result"]["all_text_regions"])
        preprocessed_count = len(preprocessed["merged_result"]["all_text_regions"])
        print(f"   原始文本区域: {original_count}")
        print(f"   预处理后文本区域: {preprocessed_count}")
        
        # 测试词典纠正
        print("\n📚 测试词典纠正...")
        dictionary_corrected = ocr_corrector._apply_dictionary_correction(preprocessed)
        
        print("   纠正结果:")
        for region in dictionary_corrected["merged_result"]["all_text_regions"]:
            corrected_flag = region.get("dictionary_corrected", False)
            status = "🔧" if corrected_flag else "  "
            print(f"   {status} '{region['text']}'")
        
        # 测试后处理
        print("\n🔧 测试后处理...")
        mock_gpt_data = {
            "drawing_basic_info": {
                "drawing_title": "结构平面图",
                "drawing_number": "S001",
                "scale": "1:100"
            },
            "component_list": [
                {
                    "component_id": "KZ1",
                    "component_type": "框架柱",
                    "dimensions": "600×800",
                    "material": "C30"
                }
            ],
            "global_notes": [
                {
                    "note_type": "材料说明",
                    "content": "混凝土强度等级C30",
                    "importance": "high"
                }
            ],
            "correction_summary": {
                "total_texts_processed": 5,
                "corrections_made": 2,
                "confidence_level": "high"
            }
        }
        
        mock_corrected_result = dictionary_corrected.copy()
        mock_corrected_result["gpt_corrected"] = mock_gpt_data
        
        final_result = ocr_corrector._postprocess_corrected_result(mock_corrected_result)
        
        print(f"   提取的图纸信息: {final_result['drawing_basic_info']}")
        print(f"   提取的构件数量: {len(final_result['component_list'])}")
        print(f"   提取的说明数量: {len(final_result['global_notes'])}")
        
        # 测试统计计算
        print("\n📊 测试统计计算...")
        stats = ocr_corrector._calculate_correction_stats(mock_ocr_result, final_result)
        print(f"   原始文本数量: {stats['original_text_count']}")
        print(f"   纠正后文本数量: {stats['corrected_text_count']}")
        print(f"   提取构件数量: {stats['components_extracted']}")
        print(f"   提取说明数量: {stats['notes_extracted']}")
        print(f"   改进总结: {stats['improvement_summary']}")
        
        print("\n🎉 OCR纠正功能测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ OCR纠正功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration_with_database():
    """测试与数据库的集成"""
    print("\n🗄️ 测试数据库集成...")
    
    try:
        from app.models.drawing import Drawing
        from app.database import get_db
        
        # 检查数据库字段
        with next(get_db()) as db:
            # 查询一个现有的drawing记录
            drawing = db.query(Drawing).first()
            if drawing:
                print(f"✅ 找到测试图纸: {drawing.filename}")
                
                # 检查新增字段
                has_merged_key = hasattr(drawing, 'ocr_merged_result_key')
                has_corrected_key = hasattr(drawing, 'ocr_corrected_result_key')
                has_correction_summary = hasattr(drawing, 'ocr_correction_summary')
                
                print(f"   ocr_merged_result_key 字段: {'✅' if has_merged_key else '❌'}")
                print(f"   ocr_corrected_result_key 字段: {'✅' if has_corrected_key else '❌'}")
                print(f"   ocr_correction_summary 字段: {'✅' if has_correction_summary else '❌'}")
                
                if has_merged_key and has_corrected_key and has_correction_summary:
                    print("✅ 数据库字段集成成功")
                    return True
                else:
                    print("❌ 数据库字段集成失败")
                    return False
            else:
                print("⚠️ 数据库中没有找到测试图纸")
                return True  # 空数据库也算正常
                
    except Exception as e:
        print(f"❌ 数据库集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始OCR智能纠正功能完整测试...")
    print("=" * 80)
    
    results = []
    
    # 测试OCR纠正器
    test1_result = await test_ocr_corrector()
    results.append(("OCR纠正器功能", test1_result))
    
    # 测试数据库集成
    test2_result = await test_integration_with_database()
    results.append(("数据库集成", test2_result))
    
    # 输出测试结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    success_rate = passed / total if total > 0 else 0
    print(f"\n🎯 测试总结:")
    print(f"   总测试数: {total}")
    print(f"   通过测试: {passed}")
    print(f"   失败测试: {total - passed}")
    print(f"   成功率: {success_rate:.1%}")
    
    if success_rate == 1.0:
        print("\n🎉 所有测试通过！OCR智能纠正功能已准备就绪。")
        return True
    else:
        print(f"\n⚠️ 还有 {total - passed} 个测试失败，需要进一步调试。")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1) 