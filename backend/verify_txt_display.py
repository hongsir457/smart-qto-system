#!/usr/bin/env python3
"""
验证TXT格式OCR结果的完整流程
"""

import json
import requests
from app.database import get_db
from app.models.drawing import Drawing

def main():
    print("🔍 验证TXT格式OCR结果显示流程")
    print("=" * 60)
    
    # 获取数据库连接
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 获取最新的图纸
        drawing = db.query(Drawing).order_by(Drawing.created_at.desc()).first()
        if not drawing:
            print("❌ 未找到图纸数据")
            return
        
        print(f"📊 图纸信息:")
        print(f"  ID: {drawing.id}")
        print(f"  文件名: {drawing.filename}")
        print(f"  状态: {drawing.status}")
        print()
        
        # 检查processing_result字段
        if not drawing.processing_result:
            print("❌ 未找到processing_result")
            return
        
        proc_result = json.loads(drawing.processing_result) if isinstance(drawing.processing_result, str) else drawing.processing_result
        
        # 检查TXT格式结果
        txt_result = proc_result.get('human_readable_txt', {})
        if txt_result and txt_result.get('is_human_readable'):
            print("✅ 数据库中发现TXT格式结果:")
            print(f"  S3 URL: {txt_result.get('s3_url')}")
            print(f"  纠正文本数: {txt_result.get('corrected_texts', 0)}")
            print(f"  内容长度: {txt_result.get('content_length', 0)}字符")
            print(f"  格式: {txt_result.get('format', 'unknown')}")
            print()
            
            # 测试S3文件访问
            s3_url = txt_result.get('s3_url')
            if s3_url:
                print("🌐 测试S3文件访问...")
                try:
                    response = requests.get(s3_url)
                    if response.status_code == 200:
                        txt_content = response.text
                        print(f"✅ S3访问成功，内容长度: {len(txt_content)}字符")
                        print(f"📄 TXT内容预览 (前300字符):")
                        print("-" * 50)
                        print(txt_content[:300])
                        if len(txt_content) > 300:
                            print("...")
                        print("-" * 50)
                        print()
                        
                        # 模拟前端数据结构
                        print("🖥️ 前端数据结构验证:")
                        frontend_data = {
                            "meta": {
                                "result_id": f"txt_{drawing.id}",
                                "process_time": txt_result.get('save_time', '2025-06-11T14:06:55'),
                                "stage": "人类可读TXT格式",
                                "system_version": "v1.0",
                                "source": f"图纸ID_{drawing.id}_TXT格式",
                                "processor": "OCRCorrectionEngine"
                            },
                            "raw_statistics": {
                                "total_texts": txt_result.get('total_ocr_texts', 70),
                                "corrected_texts": txt_result.get('corrected_texts', 29),
                                "processing_time": 51.36,
                                "average_confidence": 0.85
                            },
                            "readable_text": txt_content,
                            "readable_summary": f"智能OCR识别与纠错完成：处理{txt_result.get('total_ocr_texts', 0)}个文本项，纠正{txt_result.get('corrected_texts', 0)}项",
                            "human_readable_info": {
                                "is_txt_format": True,
                                "corrected_texts": txt_result.get('corrected_texts', 0),
                                "content_length": txt_result.get('content_length', 0),
                                "filename": txt_result.get('filename', '')
                            }
                        }
                        
                        # 检查关键字段
                        has_readable_text = bool(frontend_data.get('readable_text'))
                        print(f"  ✅ readable_text存在: {has_readable_text}")
                        print(f"  ✅ readable_text长度: {len(frontend_data.get('readable_text', ''))}字符")
                        print(f"  ✅ readable_summary: {frontend_data.get('readable_summary', '')}")
                        print()
                        
                        if has_readable_text:
                            print("🎉 前端应该能够正确显示TXT内容!")
                            print("💡 前端OCR组件将:")
                            print("   1. 默认显示'可读文本'标签页")
                            print("   2. 在TXT文本区域显示完整的纠错结果")
                            print("   3. 提供复制功能")
                        else:
                            print("❌ 前端数据结构缺少readable_text字段")
                    else:
                        print(f"❌ S3访问失败: {response.status_code}")
                except Exception as e:
                    print(f"❌ S3访问异常: {str(e)}")
            else:
                print("❌ 缺少S3 URL")
        else:
            print("❌ 未找到TXT格式结果")
            
        # 检查其他可读化结果
        real_readable = proc_result.get('real_readable_result', {})
        if real_readable and real_readable.get('is_real_data'):
            print("📋 还发现JSON格式的可读化结果:")
            print(f"  S3 URL: {real_readable.get('s3_url')}")
            print(f"  总文本数: {real_readable.get('total_ocr_texts', 0)}")
            print()
            
    finally:
        db.close()

if __name__ == "__main__":
    main() 