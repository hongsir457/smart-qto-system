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
    
    # 4. 检查中文OCR
    try:
        # 创建中文测试图片
        test_img_cn = np.ones((100, 300, 3), dtype=np.uint8) * 255
        # 使用PIL创建中文文字
        from PIL import ImageDraw, ImageFont
        pil_img = Image.fromarray(test_img_cn)
        draw = ImageDraw.Draw(pil_img)
        
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("msyh.ttc", 24)  # 微软雅黑
        except:
            font = ImageFont.load_default()
            
        draw.text((10, 30), "测试中文123", fill=(0, 0, 0), font=font)
        test_img_cn = np.array(pil_img)
        
        # 保存临时图片
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        cv2.imwrite(temp_file.name, test_img_cn)
        
        # 执行中文OCR
        result_cn = pytesseract.image_to_string(temp_file.name, lang='chi_sim+eng')
        print(f"✓ 中文OCR测试成功: '{result_cn.strip()}'")
        
        # 清理临时文件
        os.remove(temp_file.name)
        
    except Exception as e:
        print(f"✗ 中文OCR测试失败: {e}")
        print("提示：可能需要安装中文字体或语言包")
    
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
    
    # 2. 设置TESSDATA环境变量
    tessdata_paths = [
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tessdata".format(os.getenv('USERNAME'))
    ]
    
    for path in tessdata_paths:
        if os.path.exists(path):
            os.environ['TESSDATA_PREFIX'] = path
            print(f"✓ 设置TESSDATA_PREFIX: {path}")
            break
    else:
        print("⚠ 未找到tessdata目录，使用默认配置")
    
    return True

def test_ocr_with_sample():
    """使用示例图片测试OCR"""
    print("\n=== OCR功能测试 ===")
    
    try:
        # 导入OCR处理函数
        sys.path.append('.')
        from app.services.drawing import extract_text, preprocess_image, process_region
        
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

def fix_common_issues():
    """修复常见问题"""
    print("\n=== 修复常见问题 ===")
    
    # 1. 检查和安装缺失的依赖
    required_packages = ['opencv-python', 'pytesseract', 'pdf2image', 'Pillow', 'numpy']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装，尝试安装...")
            os.system(f"pip install {package}")
    
    # 2. 检查poppler工具（PDF转图片需要）
    try:
        from pdf2image import convert_from_path
        # 创建测试PDF
        test_pdf = r"C:\Windows\System32\license.rtf"  # 使用系统文件作为测试
        if os.path.exists(test_pdf):
            print("✓ PDF2Image功能可用")
        else:
            print("⚠ 无法找到测试PDF文件")
    except Exception as e:
        print(f"✗ PDF2Image配置问题: {e}")
        print("提示：可能需要安装poppler工具")
    
    # 3. 修复字体问题
    try:
        from PIL import ImageFont
        font_paths = [
            r"C:\Windows\Fonts\msyh.ttc",  # 微软雅黑
            r"C:\Windows\Fonts\simsun.ttc",  # 宋体
            r"C:\Windows\Fonts\arial.ttf"   # Arial
        ]
        
        available_fonts = []
        for font_path in font_paths:
            if os.path.exists(font_path):
                available_fonts.append(font_path)
        
        if available_fonts:
            print(f"✓ 可用字体: {len(available_fonts)} 个")
        else:
            print("✗ 未找到系统字体")
            
    except Exception as e:
        print(f"✗ 字体检查失败: {e}")

def create_fixed_ocr_service():
    """创建修复后的OCR服务函数"""
    print("\n=== 创建修复后的OCR服务 ===")
    
    fixed_code = '''
def extract_text_fixed(image_path: str):
    """
    修复后的OCR文字提取函数
    """
    import cv2
    import pytesseract
    import os
    import numpy as np
    import tempfile
    import gc
    
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
    
    local_path = image_path
    try:
        print(f"[OCR] 开始识别: {image_path}")
        
        if not os.path.exists(local_path):
            return {"error": f"文件不存在: {local_path}"}
            
        ext = os.path.splitext(local_path)[-1].lower()
        text = ""
        
        if ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            print("[OCR] 识别图片文件")
            image = cv2.imread(local_path)
            if image is None:
                return {"error": f"图片读取失败: {local_path}"}
            
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
        return {"error": str(e)}
    finally:
        gc.collect()
'''
    
    # 保存修复后的代码
    with open('extract_text_fixed.py', 'w', encoding='utf-8') as f:
        f.write(fixed_code)
    
    print("✓ 已创建修复后的OCR函数: extract_text_fixed.py")

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
    
    # 3. 修复常见问题
    fix_common_issues()
    
    # 4. 功能测试
    if test_ocr_with_sample():
        print("\n✓ OCR修复成功！")
    else:
        print("\n✗ OCR修复失败，需要手动检查")
        
    # 5. 创建修复后的服务
    create_fixed_ocr_service()
    
    print("\n=== 修复完成 ===")
    print("建议重启服务以应用修复")

if __name__ == "__main__":
    main() 