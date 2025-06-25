#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查最近Celery任务的结果
"""
import time
from celery.result import AsyncResult
from app.core.celery_app import celery_app

def main():
    print("🔍 检查最近的Celery任务结果")
    print("=" * 40)
    
    # 如果你知道任务ID，可以在这里设置
    task_id = "d3deac5e-f3d0-4923-8f84-9a6ade1f6120"  # 从之前的输出获取
    
    if task_id:
        print(f"📋 检查任务: {task_id}")
        result = AsyncResult(task_id, app=celery_app)
        
        print(f"📊 任务状态: {result.state}")
        
        if result.state == 'SUCCESS':
            try:
                task_result = result.get()
                print("✅ 任务成功完成！")
                print(f"📄 结果类型: {type(task_result)}")
                
                if isinstance(task_result, dict) and 'result' in task_result:
                    ocr_results = task_result['result'].get('ocr_results', {})
                    engine = ocr_results.get('processing_engine', '未知')
                    print(f"🔧 OCR引擎: {engine}")
                    
                    if engine == 'PaddleOCR':
                        print("🎉 成功：已切换到PaddleOCR！")
                    elif engine == 'Tesseract OCR':
                        print("⚠️  仍在使用Tesseract")
                    else:
                        print(f"❓ 未知引擎: {engine}")
                        
                    # 显示其他信息
                    if 'texts' in ocr_results:
                        print(f"📝 识别文本数量: {len(ocr_results['texts'])}")
                        if ocr_results['texts']:
                            print(f"📄 示例文本: {ocr_results['texts'][0][:50]}...")
                            
                else:
                    print("❌ 结果格式异常")
                    print(f"完整结果: {task_result}")
                    
            except Exception as e:
                print(f"❌ 获取结果失败: {e}")
                
        elif result.state == 'PENDING':
            print("⏳ 任务仍在进行中...")
        elif result.state == 'FAILURE':
            print(f"❌ 任务失败: {result.info}")
        else:
            print(f"📊 未知状态: {result.state}")
    else:
        print("❌ 没有指定任务ID")

if __name__ == "__main__":
    main() 