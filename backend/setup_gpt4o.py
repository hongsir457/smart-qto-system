#!/usr/bin/env python3
"""
GPT-4o多模态功能快速配置脚本
"""
import os
import sys
from pathlib import Path

def print_banner():
    """打印欢迎横幅"""
    print("�� 智能工程量计算系统 - GPT-4o-2024-11-20多模态配置")
    print("=" * 60)
    print("📋 配置目标：启用GPT-4o-2024-11-20图像+文本双模态分析")
    print("=" * 60)

def check_dependencies():
    """检查必要的依赖包"""
    print("\n🔍 步骤1: 检查依赖包安装状态")
    print("-" * 40)
    
    dependencies = [
        ("paddleocr", "PaddleOCR文字识别引擎"),
        ("openai", "OpenAI GPT-4o客户端"),
        ("opencv-python", "图像处理库"),
        ("pillow", "Python图像库"),
        ("numpy", "数值计算库")
    ]
    
    missing_deps = []
    
    for package, description in dependencies:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package:<15} - {description}")
        except ImportError:
            print(f"❌ {package:<15} - {description} (未安装)")
            missing_deps.append(package)
    
    if missing_deps:
        print(f"\n⚠️  发现缺失依赖: {', '.join(missing_deps)}")
        print("📦 请运行以下命令安装:")
        print(f"   pip install {' '.join(missing_deps)}")
        return False
    
    print("\n✅ 所有依赖包已正确安装")
    return True

def setup_api_key():
    """配置OpenAI API密钥"""
    print("\n🔑 步骤2: 配置OpenAI API密钥")
    print("-" * 40)
    
    # 检查现有密钥
    current_key = os.getenv("OPENAI_API_KEY")
    if current_key:
        masked_key = current_key[:12] + "..." + current_key[-4:] if len(current_key) > 16 else "***"
        print(f"🔍 当前密钥: {masked_key}")
        
        # 验证密钥格式
        if current_key.startswith("sk-") and len(current_key) > 20:
            print("✅ 密钥格式正确")
            
            # 测试密钥可用性
            if test_api_key(current_key):
                print("✅ API密钥验证成功")
                return True
            else:
                print("❌ API密钥验证失败")
        else:
            print("⚠️  密钥格式可能有误")
    
    print("\n📝 请输入您的OpenAI API密钥:")
    print("💡 提示: 密钥格式应为 sk-proj-... 或 sk-...")
    print("🔗 获取地址: https://platform.openai.com/account/api-keys")
    
    while True:
        api_key = input("\n🔑 API密钥: ").strip()
        
        if not api_key:
            print("❌ 密钥不能为空")
            continue
        
        if not api_key.startswith("sk-"):
            print("❌ 密钥格式错误，应以 'sk-' 开头")
            continue
        
        if len(api_key) < 20:
            print("❌ 密钥长度过短")
            continue
        
        # 测试密钥
        if test_api_key(api_key):
            print("✅ API密钥验证成功")
            save_api_key(api_key)
            return True
        else:
            print("❌ API密钥验证失败，请检查密钥是否正确")
            retry = input("🔄 是否重新输入? (y/n): ").strip().lower()
            if retry != 'y':
                return False

def test_api_key(api_key):
    """测试API密钥可用性"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        # 发送一个简单的测试请求 - 使用用户可用的模型
        response = client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[{"role": "user", "content": "测试连接"}],
            max_tokens=5
        )
        
        return True
        
    except Exception as e:
        print(f"⚠️  测试失败: {str(e)}")
        # 如果 gpt-4o-2024-11-20 不可用，尝试 chatgpt-4o-latest
        try:
            response = client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=5
            )
            return True
        except Exception as e2:
            print(f"⚠️  备用模型测试也失败: {str(e2)}")
            return False

def save_api_key(api_key):
    """保存API密钥到环境变量和.env文件"""
    # 设置当前会话环境变量
    os.environ["OPENAI_API_KEY"] = api_key
    
    # 保存到.env文件
    env_file = Path(".env")
    env_content = ""
    
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # 移除现有的OPENAI_API_KEY行
        lines = [line for line in lines if not line.startswith("OPENAI_API_KEY=")]
        env_content = "".join(lines)
    
    # 添加新的API密钥
    env_content += f"\nOPENAI_API_KEY={api_key}\n"
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print(f"💾 API密钥已保存到 {env_file.absolute()}")

def test_multimodal_functionality():
    """测试多模态功能"""
    print("\n🧪 步骤3: 测试多模态功能")
    print("-" * 40)
    
    try:
        # 导入测试模块
        from app.services.ai_processing.ocr_processor import OCRProcessor
        from app.services.ai_processing.gpt_analyzer import GPTAnalyzer
        
        # 初始化处理器
        print("🔧 初始化OCR处理器...")
        ocr = OCRProcessor()
        
        print("🔧 初始化GPT分析器...")
        gpt = GPTAnalyzer()
        
        # 检查功能状态
        if ocr.initialized:
            print("✅ OCR引擎初始化成功")
        else:
            print("⚠️  OCR引擎初始化失败，将使用模拟数据")
        
        if gpt.client:
            print("✅ GPT-4o客户端初始化成功")
            print(f"🤖 使用模型: {gpt.model}")
            if gpt.vision_enabled:
                print("🎯 多模态视觉功能已启用")
            else:
                print("⚠️  视觉功能未启用")
        else:
            print("❌ GPT客户端初始化失败")
            return False
        
        print("\n✅ 系统配置完成，多模态功能已就绪")
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {str(e)}")
        return False

def run_demo():
    """运行演示程序"""
    print("\n🎬 步骤4: 运行演示程序")
    print("-" * 40)
    
    demo_choice = input("🚀 是否运行演示程序? (y/n): ").strip().lower()
    
    if demo_choice == 'y':
        print("🎭 启动演示程序...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, "demo_ai_system.py"], 
                                 capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                print("✅ 演示程序运行成功")
                print(result.stdout)
            else:
                print("❌ 演示程序运行失败")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ 启动演示失败: {str(e)}")
    else:
        print("ℹ️  您可以稍后运行: python demo_ai_system.py")

def print_usage_guide():
    """打印使用指南"""
    print("\n📖 使用指南")
    print("=" * 60)
    print("🔥 功能特点:")
    print("   • GPT-4o-2024-11-20多模态图像+文本分析")
    print("   • 高精度OCR文字识别")
    print("   • 智能构件分类和尺寸提取")
    print("   • 自动工程量计算和成本估算")
    
    print("\n📝 使用方法:")
    print("   1. 命令行演示: python demo_ai_system.py")
    print("   2. 功能测试:   python test_multimodal_ai.py")
    print("   3. API接口:   启动 FastAPI 服务")
    
    print("\n📋 支持格式:")
    print("   • 图像格式: PNG, JPG, JPEG")
    print("   • 构件类型: 柱(KZ), 梁(L), 板(B), 圈梁(QL), 构造柱(GZ)")
    print("   • 尺寸标注: 400×600, 400x600, φ600等")
    
    print("\n📚 更多信息:")
    print("   • 详细文档: GPT4O_MULTIMODAL_GUIDE.md")
    print("   • 升级报告: AI_UPGRADE_REPORT.md")

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装缺失的包")
        return
    
    # 配置API密钥
    if not setup_api_key():
        print("\n❌ API密钥配置失败")
        return
    
    # 测试功能
    if not test_multimodal_functionality():
        print("\n❌ 功能测试失败")
        return
    
    # 运行演示
    run_demo()
    
    # 打印使用指南
    print_usage_guide()
    
    print("\n🎉 配置完成！GPT-4o多模态功能已就绪")
    print("=" * 60)

if __name__ == "__main__":
    main() 