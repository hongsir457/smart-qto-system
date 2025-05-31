import cv2
import numpy as np
import pytesseract
import tempfile
import os
import time

# 确保Tesseract配置正确
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "tesseract"
]

for path in tesseract_paths:
    if os.path.exists(path) or path == "tesseract":
        try:
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✓ 设置Tesseract路径: {path}")
            break
        except:
            continue

def test_ocr():
    """测试OCR功能"""
    print("=== 测试OCR功能 ===")
    
    # 创建测试图片
    test_img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    
    # 添加文字
    cv2.putText(test_img, 'Engineering Drawing', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(test_img, 'Scale: 1:100', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(test_img, 'Wall thickness: 200mm', (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # 保存测试图片
    test_file = f"test_image_{int(time.time())}.png"
    cv2.imwrite(test_file, test_img)
    
    try:
        print(f"测试图片路径: {test_file}")
        
        # 执行OCR
        result = pytesseract.image_to_string(test_file, lang='eng')
        print(f"OCR结果: '{result.strip()}'")
        
        if result.strip():
            print("✓ OCR测试成功")
            return True
        else:
            print("✗ OCR测试失败 - 无结果")
            return False
            
    except Exception as e:
        print(f"✗ OCR测试失败: {e}")
        return False
    finally:
        # 清理
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
            except:
                pass

def test_extract_text():
    """测试extract_text函数"""
    print("\n=== 测试extract_text函数 ===")
    
    try:
        # 导入修复后的函数
        from app.services.drawing import extract_text
        
        # 创建测试图片
        test_img = np.ones((200, 600, 3), dtype=np.uint8) * 255
        cv2.putText(test_img, 'Test Drawing', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(test_img, '200x300mm', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        test_file = f"test_extract_{int(time.time())}.png"
        cv2.imwrite(test_file, test_img)
        
        # 测试extract_text
        result = extract_text(test_file)
        print(f"extract_text结果: {result}")
        
        if isinstance(result, dict) and "text" in result:
            print("✓ extract_text测试成功")
            return True
        else:
            print("✗ extract_text测试失败")
            return False
            
    except Exception as e:
        print(f"✗ extract_text测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理
        if 'test_file' in locals() and os.path.exists(test_file):
            try:
                os.remove(test_file)
            except:
                pass

if __name__ == "__main__":
    print("智能QTO系统 - OCR简单测试")
    print("=" * 40)
    
    # 检查Tesseract版本
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract版本: {version}")
    except Exception as e:
        print(f"Tesseract版本检查失败: {e}")
    
    # 基本OCR测试
    test1 = test_ocr()
    
    # extract_text函数测试
    test2 = test_extract_text()
    
    if test1 and test2:
        print("\n✓ 所有测试通过，OCR功能正常")
    else:
        print("\n✗ 测试失败，需要进一步检查") 