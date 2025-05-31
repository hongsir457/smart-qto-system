import os
import sys
import cv2
import numpy as np
import pytesseract
import tempfile
from PIL import Image

def diagnose_ocr():
    """诊断OCR环境和配置"""
    print("=== OCR环境诊断 ===")
    
    # 1. 检查Tesseract版本
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract版本: {version}")
    except Exception as e:
        print(f"✗ Tesseract版本检查失败: {e}")
        return False
    
    # 2. 检查语言包
    try:
        langs = pytesseract.get_languages()
        print(f"✓ 可用语言包: {langs}")
        
        # 检查中文语言包
        if 'chi_sim' in langs:
            print("✓ 中文简体语言包已安装")
        else:
            print("✗ 中文简体语言包未安装")
            
        if 'eng' in langs:
            print("✓ 英文语言包已安装")
        else:
            print("✗ 英文语言包未安装")
            
    except Exception as e:
        print(f"✗ 语言包检查失败: {e}")
        return False
    
    # 3. 测试基本OCR功能
    try:
        # 创建测试图片
        test_img = np.ones((100, 300, 3), dtype=np.uint8) * 255
        cv2.putText(test_img, 'Test OCR 123', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # 保存临时图片
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        cv2.imwrite(temp_file.name, test_img)
        
        # 执行OCR
        result = pytesseract.image_to_string(temp_file.name, lang='eng')
        print(f"✓ 基本OCR测试成功: '{result.strip()}'")
        
        # 清理临时文件
        os.remove(temp_file.name)
        
    except Exception as e:
        print(f"✗ 基本OCR测试失败: {e}")
        return False
    
    return True

def fix_tesseract_config():
    """修复Tesseract配置问题"""
    print("\n=== 修复Tesseract配置 ===")
    
    # 1. 检查和设置Tesseract路径
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME')),
        "tesseract"  # 系统PATH中
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path) or path == "tesseract":
            try:
                pytesseract.pytesseract.tesseract_cmd = path
                version = pytesseract.get_tesseract_version()
                print(f"✓ 设置Tesseract路径: {path}")
                break
            except:
                continue
    else:
        print("✗ 未找到Tesseract可执行文件")
        print("请安装Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    return True

def test_ocr_with_sample():
    """使用示例图片测试OCR"""
    print("\n=== OCR功能测试 ===")
    
    try:
        # 导入OCR处理函数
        sys.path.append('.')
        from app.services.drawing import extract_text
        
        # 创建更复杂的测试图片
        test_img = np.ones((200, 600, 3), dtype=np.uint8) * 255
        
        # 添加一些噪声和文字
        cv2.putText(test_img, 'Engineering Drawing', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv2.putText(test_img, 'Scale: 1:100', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(test_img, 'Wall thickness: 200mm', (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # 保存测试图片
        test_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        cv2.imwrite(test_file.name, test_img)
        
        print(f"测试图片路径: {test_file.name}")
        
        # 测试extract_text函数
        result = extract_text(test_file.name)
        print(f"OCR结果: {result}")
        
        # 清理
        os.remove(test_file.name)
        
        if isinstance(result, dict) and "error" not in result:
            print("✓ OCR功能测试成功")
            return True
        else:
            print(f"✗ OCR功能测试失败: {result}")
            return False
            
    except Exception as e:
        print(f"✗ OCR功能测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_drawing_service():
    """修复drawing服务中的OCR函数"""
    print("\n=== 修复drawing服务 ===")
    
    try:
        # 读取当前的drawing.py文件
        drawing_file = 'app/services/drawing.py'
        
        # 创建修复后的extract_text函数
        fixed_extract_text = '''
def extract_text(image_path: str):
    """
    修复后的OCR文字提取函数
    """
    import os
    import cv2
    import pytesseract
    import numpy as np
    import tempfile
    import gc
    from PIL import Image
    import traceback
    
    # 确保Tesseract配置正确
    tesseract_paths = [
        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
        "tesseract"
    ]
    
    for path in tesseract_paths:
        if os.path.exists(path) or path == "tesseract":
            try:
                pytesseract.pytesseract.tesseract_cmd = path
                break
            except:
                continue
    
    try:
        print(f"[OCR] 开始识别: {image_path}")
        
        if not os.path.exists(image_path):
            return {"error": f"文件不存在: {image_path}"}
            
        ext = os.path.splitext(image_path)[-1].lower()
        text = ""
        
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            print("[OCR] 识别图片文件")
            image = cv2.imread(image_path)
            if image is None:
                return {"error": f"图片读取失败: {image_path}"}
            
            # 预处理图像
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 去噪
            denoised = cv2.medianBlur(gray, 3)
            
            # 二值化
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR配置
            config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
            
            # 尝试多种语言组合
            lang_configs = ['chi_sim+eng', 'eng', 'chi_sim']
            
            best_result = ""
            for lang in lang_configs:
                try:
                    result = pytesseract.image_to_string(binary, lang=lang, config=config)
                    if result and len(result.strip()) > len(best_result.strip()):
                        best_result = result
                except Exception as e:
                    print(f"[OCR] 语言 {lang} 识别失败: {e}")
                    continue
            
            text = best_result.strip()
            
        else:
            return {"error": f"不支持的文件格式: {ext}"}
        
        if not text:
            return {"warning": "未识别到文字内容"}
        
        # 后处理
        text = text.replace('\\n\\n', '\\n')
        text = '\\n'.join(line.strip() for line in text.split('\\n') if line.strip())
        
        return {"text": text}
        
    except Exception as e:
        print(f"[OCR] 处理失败: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        gc.collect()
'''
        
        # 保存修复后的函数到单独文件
        with open('extract_text_fixed.py', 'w', encoding='utf-8') as f:
            f.write(fixed_extract_text)
        
        print("✓ 已创建修复后的OCR函数: extract_text_fixed.py")
        print("建议替换drawing.py中的extract_text函数")
        
        return True
        
    except Exception as e:
        print(f"✗ 修复drawing服务失败: {e}")
        return False

def main():
    """主函数"""
    print("智能QTO系统 - OCR诊断和修复工具")
    print("=" * 50)
    
    # 1. 环境诊断
    if not diagnose_ocr():
        print("环境诊断失败，请检查Tesseract安装")
        return
    
    # 2. 配置修复
    if not fix_tesseract_config():
        print("配置修复失败")
        return
    
    # 3. 功能测试
    if test_ocr_with_sample():
        print("\n✓ OCR功能测试成功！")
    else:
        print("\n✗ OCR功能测试失败")
        
    # 4. 修复drawing服务
    fix_drawing_service()
    
    print("\n=== 修复完成 ===")
    print("建议重启服务以应用修复")

if __name__ == "__main__":
    main() 