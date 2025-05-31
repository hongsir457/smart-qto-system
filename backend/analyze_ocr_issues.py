import cv2
import numpy as np
import pytesseract
import tempfile
import os
import time
from PIL import Image, ImageEnhance, ImageFilter

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

def enhanced_preprocess_for_drawings(image_path):
    """
    针对建筑图纸优化的图像预处理
    """
    print("[预处理] 开始针对建筑图纸的图像预处理...")
    
    # 读取图像
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. 图像增强 - 提高对比度
    enhanced = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8)).apply(gray)
    
    # 2. 放大图像以提高OCR精度
    scale_factor = 3.0  # 放大3倍
    height, width = enhanced.shape
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    enlarged = cv2.resize(enhanced, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # 3. 去噪 - 保留文字边缘
    denoised = cv2.bilateralFilter(enlarged, 9, 75, 75)
    
    # 4. 锐化处理
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    
    # 5. 自适应二值化
    binary = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 10
    )
    
    # 6. 形态学操作 - 连接断开的文字
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # 7. 去除线条干扰（保留文字）
    # 检测水平线和垂直线
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    
    # 检测线条
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    
    # 移除线条，保留文字
    lines = cv2.add(horizontal_lines, vertical_lines)
    text_only = cv2.subtract(binary, lines)
    
    return text_only, binary, enlarged

def test_multiple_psm_modes(image, lang='chi_sim+eng'):
    """
    测试多种PSM模式，找出最佳识别结果
    """
    print("[PSM测试] 测试多种PSM模式...")
    
    # 更全面的PSM模式测试
    psm_modes = [3, 4, 6, 7, 8, 11, 12, 13]
    results = {}
    
    for psm in psm_modes:
        try:
            config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
            result = pytesseract.image_to_string(image, lang=lang, config=config)
            results[psm] = result.strip()
            print(f"PSM {psm}: {len(result.strip())} 字符")
        except Exception as e:
            print(f"PSM {psm} 失败: {e}")
            results[psm] = ""
    
    return results

def test_different_languages(image):
    """
    测试不同的语言配置
    """
    print("[语言测试] 测试不同语言配置...")
    
    lang_configs = [
        'chi_sim+eng',
        'eng+chi_sim', 
        'chi_sim',
        'eng',
        'chi_tra+eng',
        'chi_sim+chi_tra+eng'
    ]
    
    results = {}
    
    for lang in lang_configs:
        try:
            config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
            result = pytesseract.image_to_string(image, lang=lang, config=config)
            results[lang] = result.strip()
            print(f"语言 {lang}: {len(result.strip())} 字符")
        except Exception as e:
            print(f"语言 {lang} 失败: {e}")
            results[lang] = ""
    
    return results

def segment_image_for_ocr(image):
    """
    将图像分割为多个区域分别进行OCR
    """
    print("[分割] 分割图像为多个区域...")
    
    height, width = image.shape
    segments = []
    
    # 将图像分割为网格
    rows, cols = 4, 4  # 4x4网格
    row_height = height // rows
    col_width = width // cols
    
    for i in range(rows):
        for j in range(cols):
            start_row = i * row_height
            end_row = min((i + 1) * row_height, height)
            start_col = j * col_width  
            end_col = min((j + 1) * col_width, width)
            
            segment = image[start_row:end_row, start_col:end_col]
            
            # 只处理有足够内容的区域
            if segment.shape[0] > 50 and segment.shape[1] > 50:
                segments.append({
                    'image': segment,
                    'position': (i, j),
                    'coords': (start_row, end_row, start_col, end_col)
                })
    
    return segments

def extract_text_enhanced(image_path):
    """
    增强版OCR文字提取函数
    """
    try:
        print(f"[增强OCR] 开始处理: {image_path}")
        
        # 1. 图像预处理
        text_only, binary, enlarged = enhanced_preprocess_for_drawings(image_path)
        
        # 保存预处理结果以便检查
        debug_dir = "ocr_debug"
        os.makedirs(debug_dir, exist_ok=True)
        
        cv2.imwrite(f"{debug_dir}/1_enlarged.png", enlarged)
        cv2.imwrite(f"{debug_dir}/2_binary.png", binary) 
        cv2.imwrite(f"{debug_dir}/3_text_only.png", text_only)
        
        # 2. 测试多种方法
        all_results = []
        
        # 方法1: 直接OCR原始二值化图像
        print("[方法1] 直接OCR二值化图像...")
        result1 = pytesseract.image_to_string(binary, lang='chi_sim+eng', 
                                            config='--oem 3 --psm 6 -c preserve_interword_spaces=1')
        all_results.append(("方法1-二值化", result1))
        
        # 方法2: OCR去线条后的图像
        print("[方法2] OCR去线条图像...")
        result2 = pytesseract.image_to_string(text_only, lang='chi_sim+eng',
                                            config='--oem 3 --psm 6 -c preserve_interword_spaces=1')
        all_results.append(("方法2-去线条", result2))
        
        # 方法3: 分割图像OCR
        print("[方法3] 分割图像OCR...")
        segments = segment_image_for_ocr(text_only)
        segment_texts = []
        
        for i, segment in enumerate(segments):
            try:
                seg_text = pytesseract.image_to_string(segment['image'], lang='chi_sim+eng',
                                                     config='--oem 3 --psm 6 -c preserve_interword_spaces=1')
                if seg_text.strip():
                    segment_texts.append(f"[区域{segment['position']}] {seg_text.strip()}")
                    # 保存分割区域
                    cv2.imwrite(f"{debug_dir}/segment_{i}.png", segment['image'])
            except:
                continue
        
        result3 = "\n".join(segment_texts)
        all_results.append(("方法3-分割", result3))
        
        # 方法4: 测试不同PSM模式
        print("[方法4] 测试不同PSM模式...")
        psm_results = test_multiple_psm_modes(binary)
        best_psm = max(psm_results.items(), key=lambda x: len(x[1]))
        all_results.append((f"方法4-PSM{best_psm[0]}", best_psm[1]))
        
        # 方法5: 测试不同语言配置
        print("[方法5] 测试不同语言配置...")
        lang_results = test_different_languages(binary)
        best_lang = max(lang_results.items(), key=lambda x: len(x[1]))
        all_results.append((f"方法5-{best_lang[0]}", best_lang[1]))
        
        # 输出所有结果
        print("\n" + "="*50)
        print("OCR识别结果对比:")
        print("="*50)
        
        for method, result in all_results:
            print(f"\n【{method}】({len(result)}字符):")
            print("-" * 30)
            print(result[:200] + "..." if len(result) > 200 else result)
        
        # 选择最佳结果（字符数最多且合理的）
        valid_results = [(m, r) for m, r in all_results if len(r.strip()) > 10]
        if valid_results:
            best_method, best_result = max(valid_results, key=lambda x: len(x[1]))
            print(f"\n【最佳结果】选择: {best_method}")
            return {"text": best_result, "method": best_method}
        else:
            return {"warning": "所有方法都未能提取到足够的文字"}
        
    except Exception as e:
        print(f"[增强OCR] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def create_test_drawing():
    """
    创建一个模拟建筑图纸进行测试
    """
    print("[测试] 创建模拟建筑图纸...")
    
    # 创建白色背景
    img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
    
    # 绘制一些线条（模拟建筑线条）
    cv2.line(img, (100, 100), (1100, 100), (0, 0, 0), 2)
    cv2.line(img, (100, 700), (1100, 700), (0, 0, 0), 2)
    cv2.line(img, (100, 100), (100, 700), (0, 0, 0), 2)
    cv2.line(img, (1100, 100), (1100, 700), (0, 0, 0), 2)
    
    # 添加中文和英文文字标注
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'Foundation Plan 1:100', (150, 50), font, 1, (0, 0, 0), 2)
    cv2.putText(img, '200x300', (200, 150), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '4500', (500, 120), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, 'Wall A-1', (150, 400), font, 0.6, (0, 0, 0), 2)
    cv2.putText(img, 'Column C1', (800, 300), font, 0.6, (0, 0, 0), 2)
    cv2.putText(img, '3600x4800', (400, 500), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'Scale 1:100', (150, 750), font, 0.7, (0, 0, 0), 2)
    
    # 保存测试图纸
    test_file = "test_drawing.png"
    cv2.imwrite(test_file, img)
    print(f"[测试] 已保存测试图纸: {test_file}")
    
    return test_file

if __name__ == "__main__":
    print("建筑图纸OCR识别问题分析工具")
    print("=" * 50)
    
    # 创建测试图纸
    test_file = create_test_drawing()
    
    try:
        # 测试增强版OCR
        result = extract_text_enhanced(test_file)
        
        print("\n" + "="*50)
        print("最终结果:")
        print("="*50)
        print(result)
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file) 