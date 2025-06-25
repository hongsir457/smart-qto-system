#!/usr/bin/env python3
"""调试前端数据结构"""

import json
from app.database import get_db_session
from app.models.drawing import Drawing

def debug_frontend_data():
    print("🔍 检查前端将要接收的数据结构")
    print("=" * 60)
    
    session = next(get_db_session())
    try:
        drawing = session.query(Drawing).filter(Drawing.id == 1).first()
        if not drawing:
            print("❌ 图纸不存在")
            return
            
        # 模拟前端接收的数据结构
        frontend_data = {
            "id": drawing.id,
            "filename": drawing.filename,
            "status": drawing.status,
            "file_size": drawing.file_size,
            "recognition_results": drawing.recognition_results,
            "processing_result": drawing.processing_result,
            "ocr_results": drawing.ocr_results,
            "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
            "updated_at": drawing.updated_at.isoformat() if drawing.updated_at else None
        }
        
        print("📊 图纸基本信息:")
        print(f"  ID: {frontend_data['id']}")
        print(f"  文件名: {frontend_data['filename']}")
        print(f"  状态: {frontend_data['status']}")
        
        print("\n🔍 recognition_results 检查:")
        rr = frontend_data['recognition_results']
        if rr:
            print(f"  类型: {type(rr)}")
            if isinstance(rr, dict):
                print(f"  顶级字段: {list(rr.keys())}")
                
                # 检查前端期望的路径: data.recognition_results.analysis_result.analysis_summary
                if 'analysis_result' in rr:
                    ar = rr['analysis_result']
                    print(f"  analysis_result类型: {type(ar)}")
                    if isinstance(ar, dict):
                        print(f"  analysis_result字段: {list(ar.keys())}")
                        if 'analysis_summary' in ar:
                            summary = ar['analysis_summary']
                            print(f"  ✅ analysis_summary: {summary}")
                            if 'total_ocr_texts' in summary:
                                print(f"  ✅ total_ocr_texts: {summary['total_ocr_texts']}")
                            else:
                                print("  ❌ 缺少 total_ocr_texts")
                        else:
                            print("  ❌ 缺少 analysis_summary")
                    else:
                        print(f"  ❌ analysis_result不是dict: {ar}")
                else:
                    print("  ❌ 缺少 analysis_result")
                    # 检查其他可能的字段
                    if 'analysis_summary' in rr:
                        print(f"  🔍 直接的analysis_summary: {rr['analysis_summary']}")
        else:
            print("  ❌ recognition_results为空")
            
        print("\n🔍 processing_result 检查:")
        pr = frontend_data['processing_result']
        if pr:
            print(f"  类型: {type(pr)}")
            if isinstance(pr, dict):
                print(f"  字段: {list(pr.keys())}")
                if 'human_readable_txt' in pr:
                    hrt = pr['human_readable_txt']
                    print(f"  ✅ human_readable_txt: {type(hrt)}")
                    if isinstance(hrt, dict):
                        print(f"    字段: {list(hrt.keys())}")
                        if 's3_url' in hrt:
                            print(f"    ✅ S3 URL: {hrt['s3_url']}")
                        if 'is_human_readable' in hrt:
                            print(f"    ✅ is_human_readable: {hrt['is_human_readable']}")
                else:
                    print("  ❌ 缺少 human_readable_txt")
        else:
            print("  ❌ processing_result为空")
            
        print("\n🔍 模拟前端条件判断:")
        
        # 模拟前端第一个条件判断
        condition1 = (frontend_data.get('recognition_results') and 
                     frontend_data['recognition_results'].get('analysis_result') and 
                     frontend_data['recognition_results']['analysis_result'].get('analysis_summary') and 
                     frontend_data['recognition_results']['analysis_result']['analysis_summary'].get('total_ocr_texts', 0) > 0)
        print(f"  条件1 (data.recognition_results.analysis_result.analysis_summary.total_ocr_texts > 0): {condition1}")
        
        # 模拟正确的条件判断
        condition2 = (frontend_data.get('recognition_results') and 
                     frontend_data['recognition_results'].get('analysis_summary') and 
                     frontend_data['recognition_results']['analysis_summary'].get('total_ocr_texts', 0) > 0)
        print(f"  条件2 (data.recognition_results.analysis_summary.total_ocr_texts > 0): {condition2}")
        
        if condition1:
            print("  ✅ 前端应该找到OCR数据")
        elif condition2:
            print("  🔧 需要修复前端数据路径")
        else:
            print("  ❌ 前端无法找到OCR数据")
            
        print("\n📁 完整数据结构:")
        print(json.dumps(frontend_data, indent=2, ensure_ascii=False, default=str)[:2000])
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_frontend_data() 