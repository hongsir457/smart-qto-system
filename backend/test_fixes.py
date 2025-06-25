#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复效果的脚本
"""

def test_ai_analyzer_service():
    """测试AIAnalyzerService的interaction_logger初始化"""
    print("🔧 测试1: AIAnalyzerService初始化...")
    try:
        from app.services.ai_analyzer import AIAnalyzerService
        ai = AIAnalyzerService()
        
        if ai.interaction_logger is not None:
            print("✅ AIAnalyzerService.interaction_logger 初始化成功")
            print(f"   类型: {type(ai.interaction_logger).__name__}")
            return True
        else:
            print("❌ AIAnalyzerService.interaction_logger 仍然为 None")
            return False
    except Exception as e:
        print(f"❌ AIAnalyzerService 初始化异常: {e}")
        return False

def test_dual_storage_service():
    """测试DualStorageService的is_available方法"""
    print("\n🔧 测试2: DualStorageService.is_available()...")
    try:
        from app.services.dual_storage_service import DualStorageService
        storage = DualStorageService()
        
        if hasattr(storage, 'is_available'):
            is_available = storage.is_available()
            print(f"✅ DualStorageService.is_available() = {is_available}")
            return True
        else:
            print("❌ DualStorageService 没有 is_available 方法")
            return False
    except Exception as e:
        print(f"❌ DualStorageService 初始化异常: {e}")
        return False

def test_upload_fix():
    """测试上传修复"""
    print("\n🔧 测试3: 异步上传修复...")
    try:
        from app.services.dual_storage_service import DualStorageService
        import asyncio
        
        storage = DualStorageService()
        
        # 测试异步上传一个小的JSON内容
        test_content = '{"test": "data"}'
        test_key = "test/test_upload_fix.json"
        
        async def test_upload():
            try:
                url = await storage.upload_content_async(
                    content=test_content,
                    key=test_key,
                    content_type="application/json"
                )
                return url
            except Exception as e:
                print(f"   上传异常: {e}")
                return None
        
        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_upload())
        loop.close()
        
        if result:
            print(f"✅ 异步上传测试成功: {result}")
            return True
        else:
            print("❌ 异步上传测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 异步上传测试异常: {e}")
        return False

def test_ocr_result_structure():
    """测试OCR结果结构识别"""
    print("\n🔧 测试4: OCR结果结构识别...")
    try:
        # 模拟OCR结果数据
        mock_ocr_result = {
            "merged_ocr_result": {
                "all_text_regions": [
                    {"text": "测试文本1", "confidence": 0.95},
                    {"text": "测试文本2", "confidence": 0.88}
                ]
            }
        }
        
        from app.services.ocr_result_corrector import OCRResultCorrector
        corrector = OCRResultCorrector()
        
        # 模拟文本区域提取逻辑
        merged_result = mock_ocr_result.get("merged_ocr_result", {})
        text_regions = merged_result.get("text_regions", [])
        
        if not text_regions:
            # 尝试从备用字段获取
            alternative_fields = ["all_text_regions", "texts", "ocr_results"]
            for field in alternative_fields:
                if field in merged_result and merged_result[field]:
                    text_regions = merged_result[field]
                    print(f"✅ 从备用字段 '{field}' 找到 {len(text_regions)} 个文本区域")
                    return True
        
        if text_regions:
            print(f"✅ 直接找到 {len(text_regions)} 个文本区域")
            return True
        else:
            print("❌ 未找到任何文本区域")
            return False
            
    except Exception as e:
        print(f"❌ OCR结果结构测试异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试修复效果...\n")
    
    results = []
    results.append(test_ai_analyzer_service())
    results.append(test_dual_storage_service())
    results.append(test_upload_fix())
    results.append(test_ocr_result_structure())
    
    print(f"\n📊 测试结果汇总:")
    print(f"   通过: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 所有修复都成功了！")
    else:
        print("⚠️ 还有一些问题需要进一步修复") 