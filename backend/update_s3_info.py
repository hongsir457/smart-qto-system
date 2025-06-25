#!/usr/bin/env python3
"""更新数据库中的S3 TXT信息"""

from app.database import get_db
from app.models.drawing import Drawing
import json
import requests

def update_s3_info():
    print("🔧 更新数据库中的S3 TXT信息")
    print("=" * 60)
    
    # 最新的S3链接（从刚才的输出获取）
    latest_s3_url = "https://objectstorageapi.hzh.sealos.run/gkg9z6uk-smaryqto/ocr_readable_texts/c3e7b290-54ea-4fe8-9fcc-759d5d17e7fe.txt"
    
    session = next(get_db())
    try:
        drawing = session.query(Drawing).filter(Drawing.id == 1).first()
        
        if not drawing:
            print("❌ 图纸不存在")
            return
            
        print(f"📊 图纸信息: {drawing.filename}")
        
        # 首先验证S3链接是否可访问
        print(f"🔍 验证S3链接: {latest_s3_url}")
        try:
            response = requests.head(latest_s3_url, timeout=10)
            if response.status_code == 200:
                print("✅ S3文件存在且可访问")
                
                # 获取文件内容
                content_response = requests.get(latest_s3_url, timeout=10)
                if content_response.status_code == 200:
                    txt_content = content_response.text
                    print(f"✅ 获取文件内容成功，长度: {len(txt_content)} 字符")
                else:
                    print(f"❌ 获取文件内容失败: {content_response.status_code}")
                    return
            else:
                print(f"❌ S3文件不可访问: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ S3验证失败: {e}")
            return
            
        # 更新processing_result
        if isinstance(drawing.processing_result, str):
            proc_result = json.loads(drawing.processing_result)
        else:
            proc_result = drawing.processing_result
            
        # 添加human_readable_txt字段
        proc_result['human_readable_txt'] = {
            's3_url': latest_s3_url,
            'filename': 'real_ocr_readable_text_20250611_173738.txt',
            'is_human_readable': True,
            'total_ocr_texts': 72,
            'corrected_texts': 3,
            'content_length': len(txt_content),
            'save_time': '2025-06-11T17:37:38'
        }
        
        # 转换为JSON字符串保存
        drawing.processing_result = json.dumps(proc_result, ensure_ascii=False)
        
        print("💾 提交到数据库...")
        session.commit()
        
        print("✅ 数据库更新成功！")
        print(f"🎉 现在前端应该能正确显示S3上的TXT内容了")
        print(f"📁 S3链接: {latest_s3_url}")
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_s3_info() 