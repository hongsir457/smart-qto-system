"""
智能工程量计算系统演示 - GPT-4o-2024-11-20多模态版本
展示 图像分析 + OCR识别 → 构件分析 → 工程量计算 的完整流程
"""
import json
import os
import cv2
import numpy as np
from app.services.ai_processing.gpt_analyzer import GPTAnalyzer

def create_demo_drawing():
    """创建演示用的建筑图纸"""
    # 创建白色背景
    img = np.ones((800, 1200, 3), dtype=np.uint8) * 255
    
    # 绘制图纸框架
    cv2.rectangle(img, (50, 50), (1150, 750), (0, 0, 0), 2)
    
    # 绘制柱子
    cv2.rectangle(img, (150, 150), (200, 200), (0, 0, 0), 3)
    cv2.rectangle(img, (500, 150), (550, 200), (0, 0, 0), 3)
    
    # 绘制梁
    cv2.line(img, (175, 150), (525, 150), (0, 0, 0), 4)
    
    # 绘制板区域
    cv2.rectangle(img, (200, 200), (500, 400), (128, 128, 128), 1)
    
    # 添加文字标注
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # 构件信息
    texts = [
        ("KZ1 400x400", (100, 250), 1.0),
        ("L1 300x600x8000", (250, 120), 0.8),
        ("L2 250x500x6000", (250, 140), 0.8),
        ("B1 120", (350, 300), 1.0),
        ("GZ1 240x240", (600, 200), 0.8),
        ("QL1 200x300", (600, 250), 0.8),
        ("C30", (700, 150), 1.0),
        ("HRB400", (700, 180), 1.0),
        ("数量: 4根", (600, 100), 0.8),
        ("标准层", (600, 120), 0.8),
    ]
    
    for text, pos, scale in texts:
        cv2.putText(img, text, pos, font, scale, (0, 0, 0), 2)
    
    # 保存演示图片
    os.makedirs("temp", exist_ok=True)
    image_path = "temp/demo_drawing.png"
    cv2.imwrite(image_path, img)
    return image_path

def demo_ocr_data():
    """模拟OCR识别结果"""
    return {
        'success': True,
        'recognized_texts': [
            {'text': 'KZ1 400x400', 'confidence': 0.89, 'bbox': [100, 250, 200, 280]},
            {'text': 'L1 300x600x8000', 'confidence': 0.97, 'bbox': [250, 120, 380, 140]},
            {'text': 'L2 250x500x6000', 'confidence': 0.95, 'bbox': [250, 140, 370, 160]},
            {'text': 'B1 120', 'confidence': 1.00, 'bbox': [350, 300, 400, 320]},
            {'text': 'GZ1 240x240', 'confidence': 0.92, 'bbox': [600, 200, 700, 220]},
            {'text': 'QL1 200x300', 'confidence': 0.88, 'bbox': [600, 250, 700, 270]},
            {'text': 'C30', 'confidence': 0.98, 'bbox': [700, 150, 730, 170]},
            {'text': 'HRB400', 'confidence': 1.00, 'bbox': [700, 180, 760, 200]},
            {'text': '数量: 4根', 'confidence': 0.85, 'bbox': [600, 100, 680, 120]},
            {'text': '标准层', 'confidence': 0.90, 'bbox': [600, 120, 660, 140]}
        ],
        'processing_time': 1.2,
        'total_regions': 10
    }

def demo_ai_recognition():
    """演示完整的AI识别流程"""
    print("🚀 智能工程量计算系统演示")
    print("=" * 80)
    print("📋 系统功能：图纸识别 → 构件分析 → 工程量计算 → 成本估算")
    print("=" * 80)
    
    # 创建演示图像
    image_path = create_demo_drawing()
    print(f"🖼️  演示图纸: {image_path}")
    
    # 步骤1: OCR文字识别
    print("\n🔍 步骤1: PaddleOCR文字识别")
    print("-" * 40)
    ocr_data = demo_ocr_data()
    
    texts = ocr_data['recognized_texts']
    print(f"✅ 识别成功！共识别 {len(texts)} 个文本区域")
    print(f"⏱️  处理时间：{ocr_data['processing_time']}秒")
    print()
    
    print("📝 识别的文本内容：")
    for i, text_info in enumerate(texts, 1):
        text = text_info['text']
        confidence = text_info['confidence']
        category = get_text_category(text)
        print(f"   {i:2d}. '{text}' (置信度: {confidence:.2f}) [{category}]")
    
    # 步骤2: 智能构件分析
    print(f"\n🧠 步骤2: 智能构件分析")
    print("-" * 40)
    analyzer = GPTAnalyzer()
    
    # 显示分析模式
    if analyzer.vision_enabled:
        mode = f"GPT-4o多模态模式 (图像+文本)"
        print(f"🤖 分析模型: {analyzer.model}")
        print(f"👁️  视觉分析: 启用")
    elif analyzer.ai_enabled:
        mode = f"AI文本模式"
        print(f"🤖 分析模型: {analyzer.model}")
    else:
        mode = "智能规则引擎"
    
    print(f"🔧 分析模式：{mode}")
    
    # 执行分析 - 如果有图像且支持多模态，使用图像分析
    if analyzer.vision_enabled and os.path.exists(image_path):
        print("🖼️  启用多模态分析: 图像 + OCR文本")
        analysis_result = analyzer.analyze_components(ocr_data, image_path)
    else:
        analysis_result = analyzer.analyze_components(ocr_data)
    
    if analysis_result.get('success'):
        components = analysis_result.get('components', [])
        engine = analysis_result.get('engine_version', analysis_result.get('model_used', 'unknown'))
        vision_used = analysis_result.get('vision_analysis', False)
        
        print(f"✅ 分析成功！识别到 {len(components)} 个构件")
        print(f"📦 分析引擎：{engine}")
        if vision_used:
            print(f"👁️  视觉增强：图像+文本交叉验证")
        print()
        
        if components:
            print("📋 构件清单：")
            print("=" * 80)
            print(f"{'序号':<4} {'构件编号':<15} {'类型':<10} {'尺寸':<20} {'材料':<10} {'置信度':<8}")
            print("-" * 80)
            
            for i, comp in enumerate(components, 1):
                code = comp.get('code', 'N/A')[:14]
                comp_type = comp.get('type', 'N/A')[:9]
                dimensions = comp.get('dimensions', 'N/A')[:19]
                material = comp.get('material', '未指定')[:9]
                confidence = comp.get('confidence', 0)
                
                print(f"{i:<4} {code:<15} {comp_type:<10} {dimensions:<20} {material:<10} {confidence:<8.2f}")
        
        # 步骤3: 工程量计算
        if components:
            print(f"\n📊 步骤3: 工程量计算")
            print("-" * 40)
            
            quantity_result = analyzer.calculate_quantities(components)
            
            if quantity_result.get('success'):
                calc_mode = quantity_result.get('calculation_mode', 'unknown')
                print(f"🔧 计算模式：{calc_mode}")
                print("✅ 工程量计算成功！")
                print()
                
                # 显示工程量汇总
                concrete = quantity_result.get('concrete_volume', 0)
                steel = quantity_result.get('steel_weight', 0)
                formwork = quantity_result.get('formwork_area', 0)
                
                print("📊 工程量汇总：")
                print("=" * 50)
                print(f"🏗️  混凝土体积：{concrete:>12.3f} m³")
                print(f"🔩 钢筋重量：  {steel:>12.3f} t")
                print(f"📏 模板面积：  {formwork:>12.3f} m²")
                print("=" * 50)
                
                # 步骤4: 成本估算
                print(f"\n💰 步骤4: 成本估算")
                print("-" * 40)
                
                # 市场价格（示例）
                concrete_price = 350  # 元/m³
                steel_price = 4500    # 元/t
                formwork_price = 45   # 元/m²
                
                concrete_cost = concrete * concrete_price
                steel_cost = steel * steel_price
                formwork_cost = formwork * formwork_price
                
                material_total = concrete_cost + steel_cost + formwork_cost
                labor_cost = material_total * 0.4  # 人工费按材料费40%估算
                machinery_cost = material_total * 0.15  # 机械费按材料费15%估算
                total_cost = material_total + labor_cost + machinery_cost
                
                print("💵 分项成本：")
                print("=" * 60)
                print(f"混凝土：  {concrete:>8.2f} m³ × ¥{concrete_price:>4}/m³ = ¥{concrete_cost:>10,.0f}")
                print(f"钢筋：    {steel:>8.2f} t  × ¥{steel_price:>4}/t  = ¥{steel_cost:>10,.0f}")
                print(f"模板：    {formwork:>8.2f} m² × ¥{formwork_price:>4}/m² = ¥{formwork_cost:>10,.0f}")
                print("-" * 60)
                print(f"材料费小计：                        ¥{material_total:>10,.0f}")
                print(f"人工费 (40%)：                      ¥{labor_cost:>10,.0f}")
                print(f"机械费 (15%)：                      ¥{machinery_cost:>10,.0f}")
                print("=" * 60)
                print(f"工程总造价：                        ¥{total_cost:>10,.0f}")
                print("=" * 60)
                
                # 生成报告摘要
                print(f"\n📋 项目摘要")
                print("-" * 40)
                print(f"• 图纸类型：结构施工图")
                print(f"• 识别构件：{len(components)} 个")
                print(f"• 主要材料：C30混凝土、HRB400钢筋")
                print(f"• 工程规模：中小型框架结构")
                print(f"• 预估造价：¥{total_cost:,.0f}")
                print(f"• 单方造价：¥{total_cost/max(concrete, 1):,.0f}/m³混凝土")
                
                # 显示技术优势
                if vision_used:
                    print(f"\n🔬 多模态分析优势")
                    print("-" * 40)
                    print(f"• 图像理解：空间关系、构件布局")
                    print(f"• 文本验证：OCR识别结果交叉验证")
                    print(f"• 智能补全：遗漏信息自动识别")
                    print(f"• 精度提升：综合置信度评估")
                
            else:
                print(f"❌ 工程量计算失败：{quantity_result.get('error', '未知错误')}")
        else:
            print("⚠️  没有识别到有效构件，无法进行工程量计算")
    else:
        print(f"❌ 构件分析失败：{analysis_result.get('error', '未知错误')}")
    
    print(f"\n🎉 演示完成！")
    print("=" * 80)
    print("💡 系统特点：")
    print("   • GPT-4o多模态图像+文本分析")
    print("   • 支持中文建筑图纸OCR识别")
    print("   • 智能构件分类和尺寸提取")
    print("   • 自动工程量计算")
    print("   • 实时成本估算")
    print("   • 三层容错：AI → 规则引擎 → 降级处理")
    print("=" * 80)
    
    # 清理演示文件
    try:
        os.remove(image_path)
        print("🧹 演示文件已清理")
    except:
        pass

def get_text_category(text):
    """获取文本分类"""
    if any(prefix in text.upper() for prefix in ['KZ', 'L', 'B', 'GZ', 'QL']):
        return "构件编号"
    elif any(mat in text.upper() for mat in ['C25', 'C30', 'C35']):
        return "混凝土等级"
    elif any(steel in text.upper() for steel in ['HRB400', 'HRB500', 'HPB300']):
        return "钢筋等级"
    elif "数量" in text or "根" in text:
        return "数量信息"
    elif any(pos in text for pos in ['层', '区', '段']):
        return "位置信息"
    else:
        return "其他"

if __name__ == "__main__":
    demo_ai_recognition() 