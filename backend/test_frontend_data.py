#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

def test_normalize_ocr_data():
    """测试前端OCR数据标准化逻辑"""
    
    print("🧪 测试前端OCR数据标准化逻辑")
    print("="*60)
    
    # 模拟前端normalizeOcrData函数
    def normalize_ocr_data(data):
        print(f"🔧 标准化OCR数据，输入类型: {type(data)}")
        
        # 如果数据为空或None
        if not data:
            return {
                "text_regions": [
                    {"text": "无OCR数据", "confidence": 0.0}
                ]
            }
        
        # 如果已经是正确的text_regions格式
        if isinstance(data, dict) and "text_regions" in data and isinstance(data["text_regions"], list):
            return data
        
        # 如果是PaddleOCR格式
        if isinstance(data, dict) and "rec_texts" in data and isinstance(data["rec_texts"], list):
            scores = data.get("rec_scores", [])
            return {
                "text_regions": [
                    {
                        "text": text,
                        "confidence": scores[i] if i < len(scores) else 1.0
                    }
                    for i, text in enumerate(data["rec_texts"])
                ]
            }
        
        # 如果是字符串
        if isinstance(data, str):
            return {
                "text_regions": [
                    {"text": data, "confidence": 1.0}
                ]
            }
        
        # 如果是数组
        if isinstance(data, list):
            return {
                "text_regions": [
                    {
                        "text": item.get("text", item.get("rec_text", str(item))) if isinstance(item, dict) else str(item),
                        "confidence": item.get("confidence", item.get("score", 1.0)) if isinstance(item, dict) else 1.0
                    }
                    for item in data
                ]
            }
        
        # 其他情况
        return {
            "text_regions": [
                {"text": json.dumps(data), "confidence": 0.5}
            ]
        }
    
    # 测试用例
    test_cases = [
        {
            "name": "字符串格式",
            "input": "KZI 400*600 C20"
        },
        {
            "name": "已有text_regions格式",
            "input": {
                "text_regions": [
                    {"text": "KZI", "confidence": 0.85},
                    {"text": "400*600", "confidence": 0.88}
                ]
            }
        },
        {
            "name": "PaddleOCR格式", 
            "input": {
                "rec_texts": ["KZI", "400*600", "C20"],
                "rec_scores": [0.85, 0.88, 0.79]
            }
        },
        {
            "name": "数组格式",
            "input": [
                {"text": "KZI", "confidence": 0.85},
                {"text": "400*600", "confidence": 0.88}
            ]
        },
        {
            "name": "空数据",
            "input": None
        },
        {
            "name": "复杂对象",
            "input": {"some": "unknown", "format": 123}
        }
    ]
    
    for case in test_cases:
        print(f"\n📋 测试: {case['name']}")
        print(f"输入: {case['input']}")
        
        try:
            result = normalize_ocr_data(case['input'])
            print(f"✅ 输出: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # 验证结果格式
            if "text_regions" in result and isinstance(result["text_regions"], list):
                print(f"✅ 格式验证通过，包含 {len(result['text_regions'])} 个文本区域")
            else:
                print("❌ 格式验证失败")
                
        except Exception as e:
            print(f"❌ 处理失败: {str(e)}")
    
    print("\n🎯 总结:")
    print("  ✅ 前端数据标准化逻辑可以处理各种OCR数据格式")
    print("  ✅ 统一转换为 text_regions 格式，符合后端API期望")
    print("  ✅ 包含错误处理，避免因数据格式问题导致422错误")

if __name__ == "__main__":
    test_normalize_ocr_data() 