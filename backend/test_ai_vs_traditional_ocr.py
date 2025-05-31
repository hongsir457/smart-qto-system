#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI OCR vs 传统OCR 对比测试脚本
"""

import os
import sys
import time
import json
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ocr_comparison(image_path, test_ai=True):
    """对比测试传统OCR和AI OCR"""
    
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return
    
    print(f"\n{'='*80}")
    print(f"OCR识别效果对比测试")
    print(f"测试图片: {os.path.basename(image_path)}")
    print(f"{'='*80}")
    
    results = {}
    
    # 1. 测试传统OCR
    print(f"\n🔧 传统OCR测试")
    print("-" * 50)
    
    try:
        from app.services.drawing import extract_text
        
        start_time = time.time()
        traditional_result = extract_text(image_path, use_ai=False)
        traditional_time = time.time() - start_time
        
        if "error" in traditional_result:
            print(f"❌ 传统OCR失败: {traditional_result['error']}")
            results['traditional'] = {"error": traditional_result['error']}
        else:
            traditional_text = traditional_result.get("text", "")
            print(f"✅ 传统OCR成功")
            print(f"识别文字长度: {len(traditional_text)} 字符")
            print(f"处理时间: {traditional_time:.2f} 秒")
            
            if traditional_text:
                print(f"\n📝 识别内容预览:")
                preview = traditional_text[:300]
                if len(traditional_text) > 300:
                    preview += "\n... (内容过长，已截断)"
                print(preview)
            
            results['traditional'] = {
                "text": traditional_text,
                "length": len(traditional_text),
                "time": traditional_time,
                "success": True
            }
            
    except Exception as e:
        print(f"❌ 传统OCR测试失败: {str(e)}")
        results['traditional'] = {"error": str(e)}
    
    # 2. 测试AI OCR (如果启用)
    if test_ai:
        print(f"\n🤖 AI OCR测试")
        print("-" * 50)
        
        # 检查是否有可用的AI服务
        ai_providers = []
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "claude": "CLAUDE_API_KEY", 
            "baidu": "BAIDU_API_KEY",
            "qwen": "QWEN_API_KEY"
        }
        
        for provider, env_var in env_vars.items():
            if os.getenv(env_var):
                ai_providers.append(provider)
        
        if not ai_providers:
            print("⚠️ 未配置AI服务API密钥，跳过AI OCR测试")
            print("请设置以下环境变量之一:")
            for provider, env_var in env_vars.items():
                print(f"  - {env_var} (for {provider})")
            results['ai'] = {"error": "未配置AI API密钥"}
        else:
            print(f"🔍 检测到可用AI服务: {', '.join(ai_providers)}")
            
            try:
                start_time = time.time()
                ai_result = extract_text(image_path, use_ai=True, ai_provider="auto")
                ai_time = time.time() - start_time
                
                if "error" in ai_result:
                    print(f"❌ AI OCR失败: {ai_result['error']}")
                    results['ai'] = {"error": ai_result['error']}
                else:
                    ai_text = ai_result.get("text", "")
                    ai_provider = ai_result.get("provider", "unknown")
                    ai_model = ai_result.get("model", "unknown")
                    ai_tokens = ai_result.get("tokens_used", 0)
                    
                    print(f"✅ AI OCR成功")
                    print(f"使用服务: {ai_provider} ({ai_model})")
                    print(f"识别文字长度: {len(ai_text)} 字符")
                    print(f"处理时间: {ai_time:.2f} 秒")
                    print(f"Token消耗: {ai_tokens}")
                    
                    if ai_text:
                        print(f"\n📝 识别内容预览:")
                        preview = ai_text[:300]
                        if len(ai_text) > 300:
                            preview += "\n... (内容过长，已截断)"
                        print(preview)
                    
                    results['ai'] = {
                        "text": ai_text,
                        "length": len(ai_text),
                        "time": ai_time,
                        "provider": ai_provider,
                        "model": ai_model,
                        "tokens": ai_tokens,
                        "success": True
                    }
                    
            except Exception as e:
                print(f"❌ AI OCR测试失败: {str(e)}")
                results['ai'] = {"error": str(e)}
    
    # 3. 对比分析
    print(f"\n📊 对比分析")
    print("=" * 50)
    
    if results.get('traditional', {}).get('success') and results.get('ai', {}).get('success'):
        traditional_data = results['traditional']
        ai_data = results['ai']
        
        print(f"识别长度对比:")
        print(f"  传统OCR: {traditional_data['length']} 字符")
        print(f"  AI OCR:   {ai_data['length']} 字符")
        
        if ai_data['length'] > traditional_data['length']:
            improvement = ((ai_data['length'] - traditional_data['length']) / traditional_data['length']) * 100
            print(f"  📈 AI OCR比传统OCR多识别了 {improvement:.1f}%")
        elif traditional_data['length'] > ai_data['length']:
            reduction = ((traditional_data['length'] - ai_data['length']) / traditional_data['length']) * 100
            print(f"  📉 AI OCR比传统OCR少识别了 {reduction:.1f}%")
        else:
            print(f"  🟡 两种方法识别长度相同")
        
        print(f"\n处理时间对比:")
        print(f"  传统OCR: {traditional_data['time']:.2f} 秒")
        print(f"  AI OCR:   {ai_data['time']:.2f} 秒")
        
        if ai_data['time'] < traditional_data['time']:
            print(f"  ⚡ AI OCR更快")
        else:
            print(f"  🐌 传统OCR更快")
        
        # 分析内容质量
        print(f"\n内容质量分析:")
        traditional_text = traditional_data['text'].lower()
        ai_text = ai_data['text'].lower()
        
        # 检查建筑关键词
        building_keywords = [
            'foundation', 'plan', 'scale', 'wall', 'column', 'beam', 
            'kitchen', 'bedroom', 'bathroom', 'garage', 'storage',
            'concrete', 'steel', 'grade', 'dimension', 'depth',
            'living', 'room', 'type', 'mm', 'notes'
        ]
        
        traditional_keywords = [kw for kw in building_keywords if kw in traditional_text]
        ai_keywords = [kw for kw in building_keywords if kw in ai_text]
        
        print(f"  传统OCR识别关键词: {len(traditional_keywords)}/12")
        print(f"  AI OCR识别关键词:   {len(ai_keywords)}/12")
        
        if len(ai_keywords) > len(traditional_keywords):
            print(f"  🎯 AI OCR在关键词识别上更好")
        elif len(traditional_keywords) > len(ai_keywords):
            print(f"  🎯 传统OCR在关键词识别上更好")
        else:
            print(f"  🟡 两种方法关键词识别相当")
        
        # 数字识别对比
        import re
        traditional_numbers = re.findall(r'\b\d+\b', traditional_text)
        ai_numbers = re.findall(r'\b\d+\b', ai_text)
        
        print(f"  传统OCR识别数字: {len(traditional_numbers)} 个")
        print(f"  AI OCR识别数字:   {len(ai_numbers)} 个")
        
    elif results.get('traditional', {}).get('success'):
        print("✅ 传统OCR成功，AI OCR失败")
    elif results.get('ai', {}).get('success'):
        print("✅ AI OCR成功，传统OCR失败")
    else:
        print("❌ 两种方法都失败了")
    
    # 4. 建议
    print(f"\n💡 使用建议")
    print("-" * 30)
    
    if results.get('ai', {}).get('success'):
        print("🤖 推荐使用AI OCR:")
        print("  - 更高的识别准确率")
        print("  - 更好的结构化理解")
        print("  - 更强的上下文理解能力")
        if results.get('ai', {}).get('tokens', 0) > 0:
            print(f"  - 成本考虑: 约{results['ai']['tokens']}个token")
    else:
        print("🔧 建议使用传统OCR:")
        print("  - 本地处理，无网络依赖")
        print("  - 无API调用成本")
        print("  - 处理速度较快")
    
    return results

def main():
    """主函数"""
    print("🔬 AI OCR vs 传统OCR 对比测试工具")
    print("=" * 80)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        test_ocr_comparison(image_path)
    else:
        print("\n使用方法:")
        print("python test_ai_vs_traditional_ocr.py <图片路径>")
        print("\n示例:")
        print("python test_ai_vs_traditional_ocr.py test_drawing.png")
        
        # 查找当前目录下的图片文件进行演示
        current_dir = Path('.')
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(current_dir.glob(f'*{ext}'))
            image_files.extend(current_dir.glob(f'*{ext.upper()}'))
        
        if image_files:
            print(f"\n🔍 在当前目录找到以下图片文件:")
            for i, img_file in enumerate(image_files[:5], 1):  # 最多显示5个
                print(f"  {i}. {img_file.name}")
            
            if len(image_files) > 5:
                print(f"  ... 还有 {len(image_files) - 5} 个文件")
            
            print(f"\n选择一个文件进行测试，或直接运行:")
            print(f"python test_ai_vs_traditional_ocr.py {image_files[0].name}")

if __name__ == "__main__":
    main() 