import tempfile
import cv2
import numpy as np
import asyncio
import os

def create_test_image():
    """创建测试图像"""
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    cv2.putText(img, "FINAL SIMPLE TEST", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    cv2.imwrite(temp_file.name, img)
    return temp_file.name

async def test_ocr_function():
    """测试OCR函数"""
    print("🧪 最简单OCR测试...")
    
    test_image_path = create_test_image()
    print(f"📄 测试图像: {test_image_path}")
    
    try:
        from app.tasks.ocr_tasks import _perform_traditional_ocr
        print("✅ 导入成功")
        
        # 直接调用OCR函数
        result = await _perform_traditional_ocr("simple_test", test_image_path)
        
        print(f"📊 结果类型: {type(result)}")
        if isinstance(result, dict):
            engine = result.get('processing_engine', '未知')
            print(f"🔧 OCR引擎: {engine}")
            
            if engine == 'PaddleOCR':
                print("✅ 成功！PaddleOCR正常工作！")
                return True
            else:
                print(f"❌ 错误引擎: {engine}")
                return False
        else:
            print(f"❌ 异常结果: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_image_path):
            os.unlink(test_image_path)

def main():
    print("=" * 40)
    print("🧪 最终简单测试")
    print("=" * 40)
    
    success = asyncio.run(test_ocr_function())
    
    print("=" * 40)
    if success:
        print("🎉 测试成功！")
    else:
        print("💥 测试失败！")
    print("=" * 40)

if __name__ == "__main__":
    main() 