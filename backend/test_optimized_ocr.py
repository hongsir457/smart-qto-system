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

def create_complex_drawing():
    """创建一个复杂的建筑图纸测试图像"""
    print("[创建] 生成复杂建筑图纸...")
    
    # 创建大尺寸白色背景
    img = np.ones((1000, 1400, 3), dtype=np.uint8) * 255
    
    # 绘制主要结构线条
    # 外框
    cv2.rectangle(img, (100, 100), (1300, 900), (0, 0, 0), 2)
    
    # 内部分割线
    cv2.line(img, (100, 300), (1300, 300), (0, 0, 0), 1)
    cv2.line(img, (100, 600), (1300, 600), (0, 0, 0), 1)
    cv2.line(img, (400, 100), (400, 900), (0, 0, 0), 1)
    cv2.line(img, (700, 100), (700, 900), (0, 0, 0), 1)
    cv2.line(img, (1000, 100), (1000, 900), (0, 0, 0), 1)
    
    # 添加细线条（模拟详细绘图）
    for i in range(5):
        y = 350 + i * 30
        cv2.line(img, (150, y), (350, y), (128, 128, 128), 1)
    
    # 添加各种文字标注（模拟真实建筑图纸）
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # 标题区域
    cv2.putText(img, 'FOUNDATION PLAN', (120, 50), font, 1.2, (0, 0, 0), 2)
    cv2.putText(img, 'Scale: 1:100', (120, 80), font, 0.8, (0, 0, 0), 2)
    
    # 尺寸标注
    cv2.putText(img, '4500', (200, 130), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, '3600', (500, 130), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, '4800', (800, 130), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, '3000', (1100, 130), font, 0.7, (0, 0, 0), 2)
    
    # 构件标注
    cv2.putText(img, 'Wall A-1', (120, 200), font, 0.6, (0, 0, 0), 2)
    cv2.putText(img, 'Type: 200mm RC', (120, 220), font, 0.5, (0, 0, 0), 1)
    
    cv2.putText(img, 'Column C1', (420, 200), font, 0.6, (0, 0, 0), 2)
    cv2.putText(img, '400x400', (420, 220), font, 0.5, (0, 0, 0), 1)
    
    cv2.putText(img, 'Beam B-1', (720, 200), font, 0.6, (0, 0, 0), 2)
    cv2.putText(img, '300x600', (720, 220), font, 0.5, (0, 0, 0), 1)
    
    cv2.putText(img, 'Foundation F1', (1020, 200), font, 0.6, (0, 0, 0), 2)
    cv2.putText(img, '1200x1200x600', (1020, 220), font, 0.5, (0, 0, 0), 1)
    
    # 中间区域标注
    cv2.putText(img, 'Living Room', (200, 450), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '6000x4500', (200, 480), font, 0.6, (0, 0, 0), 1)
    
    cv2.putText(img, 'Kitchen', (500, 450), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '3600x3000', (500, 480), font, 0.6, (0, 0, 0), 1)
    
    cv2.putText(img, 'Bedroom 1', (800, 450), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '4800x3600', (800, 480), font, 0.6, (0, 0, 0), 1)
    
    cv2.putText(img, 'Bathroom', (1100, 450), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '2400x2100', (1100, 480), font, 0.6, (0, 0, 0), 1)
    
    # 下方区域标注
    cv2.putText(img, 'Garage', (200, 750), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '7200x6000', (200, 780), font, 0.6, (0, 0, 0), 1)
    
    cv2.putText(img, 'Storage', (800, 750), font, 0.8, (0, 0, 0), 2)
    cv2.putText(img, '3000x2400', (800, 780), font, 0.6, (0, 0, 0), 1)
    
    # 技术说明
    cv2.putText(img, 'NOTES:', (120, 950), font, 0.7, (0, 0, 0), 2)
    cv2.putText(img, '1. All dimensions in mm', (120, 980), font, 0.5, (0, 0, 0), 1)
    cv2.putText(img, '2. Concrete grade: C30', (400, 980), font, 0.5, (0, 0, 0), 1)
    cv2.putText(img, '3. Steel grade: HRB400', (700, 980), font, 0.5, (0, 0, 0), 1)
    cv2.putText(img, '4. Foundation depth: 1500mm', (1000, 980), font, 0.5, (0, 0, 0), 1)
    
    # 添加一些建筑符号和小字
    cv2.putText(img, 'N', (1250, 150), font, 1.0, (0, 0, 0), 2)  # 指北针
    cv2.circle(img, (1250, 170), 20, (0, 0, 0), 2)
    
    # 保存测试图纸
    test_file = "complex_drawing.png"
    cv2.imwrite(test_file, img)
    print(f"[创建] 已保存复杂建筑图纸: {test_file}")
    
    return test_file

def test_original_vs_optimized():
    """对比原始方法和优化方法的OCR效果"""
    print("\n" + "="*60)
    print("OCR方法对比测试")
    print("="*60)
    
    # 创建测试图纸
    test_file = create_complex_drawing()
    
    try:
        # 导入优化后的extract_text函数
        from app.services.drawing import extract_text
        
        print("\n[测试] 使用优化后的OCR方法...")
        start_time = time.time()
        
        optimized_result = extract_text(test_file)
        optimized_time = time.time() - start_time
        
        print(f"\n优化方法结果:")
        print("-" * 40)
        if isinstance(optimized_result, dict):
            if "text" in optimized_result:
                text = optimized_result["text"]
                print(f"识别文字长度: {len(text)} 字符")
                print(f"处理时间: {optimized_time:.2f} 秒")
                print("\n识别内容预览:")
                print(text[:500] + "..." if len(text) > 500 else text)
                
                # 统计识别到的关键词
                keywords = ['foundation', 'plan', 'scale', 'wall', 'column', 'beam', 
                           'living', 'kitchen', 'bedroom', 'bathroom', 'garage', 'storage']
                found_keywords = [kw for kw in keywords if kw.lower() in text.lower()]
                print(f"\n识别到的关键词: {found_keywords}")
                print(f"关键词识别率: {len(found_keywords)}/{len(keywords)} ({len(found_keywords)/len(keywords)*100:.1f}%)")
                
            elif "error" in optimized_result:
                print(f"识别失败: {optimized_result['error']}")
            elif "warning" in optimized_result:
                print(f"识别警告: {optimized_result['warning']}")
        
        # 简单方法对比
        print(f"\n[对比] 使用简单OCR方法...")
        start_time = time.time()
        
        image = cv2.imread(test_file)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        simple_result = pytesseract.image_to_string(binary, lang='chi_sim+eng')
        simple_time = time.time() - start_time
        
        print(f"\n简单方法结果:")
        print("-" * 40)
        print(f"识别文字长度: {len(simple_result)} 字符")
        print(f"处理时间: {simple_time:.2f} 秒")
        print("\n识别内容预览:")
        print(simple_result[:500] + "..." if len(simple_result) > 500 else simple_result)
        
        # 统计简单方法的关键词
        simple_keywords = [kw for kw in keywords if kw.lower() in simple_result.lower()]
        print(f"\n识别到的关键词: {simple_keywords}")
        print(f"关键词识别率: {len(simple_keywords)}/{len(keywords)} ({len(simple_keywords)/len(keywords)*100:.1f}%)")
        
        # 总结对比
        print(f"\n" + "="*60)
        print("对比总结:")
        print("="*60)
        
        if isinstance(optimized_result, dict) and "text" in optimized_result:
            opt_len = len(optimized_result["text"])
            opt_kw = len(found_keywords)
        else:
            opt_len = 0
            opt_kw = 0
            
        simple_len = len(simple_result)
        simple_kw = len(simple_keywords)
        
        print(f"文字识别量: 优化方法 {opt_len} vs 简单方法 {simple_len}")
        print(f"关键词识别: 优化方法 {opt_kw} vs 简单方法 {simple_kw}")
        print(f"处理时间: 优化方法 {optimized_time:.2f}s vs 简单方法 {simple_time:.2f}s")
        
        if opt_len > simple_len:
            print("✅ 优化方法在文字识别量上表现更好")
        elif simple_len > opt_len:
            print("⚠️ 简单方法在文字识别量上表现更好")
        else:
            print("🟡 两种方法在文字识别量上相当")
            
        if opt_kw > simple_kw:
            print("✅ 优化方法在关键词识别上表现更好")
        elif simple_kw > opt_kw:
            print("⚠️ 简单方法在关键词识别上表现更好")
        else:
            print("🟡 两种方法在关键词识别上相当")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    print("建筑图纸OCR优化效果测试")
    print("="*60)
    
    # 检查Tesseract版本
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract版本: {version}")
    except Exception as e:
        print(f"Tesseract版本检查失败: {e}")
        exit(1)
    
    # 运行对比测试
    test_original_vs_optimized() 