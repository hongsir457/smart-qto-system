#!/usr/bin/env python3
"""
批量修复drawings.processing_result，补全human_readable_txt字段（含s3_url等S3元数据）
"""
from app.database import get_db
from app.models.drawing import Drawing
import json
import requests

def fix_processing_result_s3_url():
    session = next(get_db())
    drawings = session.query(Drawing).all()
    fixed = 0
    for drawing in drawings:
        pr = drawing.processing_result
        if not pr:
            continue
        if isinstance(pr, str):
            try:
                pr = json.loads(pr)
            except Exception:
                continue
        # 跳过已存在human_readable_txt且有s3_url的
        if 'human_readable_txt' in pr and pr['human_readable_txt'].get('s3_url'):
            continue
        # 尝试查找real_ocr_txt/real_readable_result/sealos_storage等字段
        s3_url = None
        for key in ['human_readable_txt', 'real_ocr_txt', 'real_readable_result', 'sealos_storage']:
            if key in pr and pr[key].get('s3_url'):
                s3_url = pr[key]['s3_url']
                break
        if not s3_url:
            continue
        # 验证S3链接可用
        try:
            resp = requests.head(s3_url, timeout=10)
            if resp.status_code != 200:
                continue
        except Exception:
            continue
        # 获取内容长度
        try:
            txt_resp = requests.get(s3_url, timeout=10)
            content_length = len(txt_resp.text) if txt_resp.status_code == 200 else 0
        except Exception:
            content_length = 0
        # 补全human_readable_txt字段
        pr['human_readable_txt'] = {
            's3_url': s3_url,
            'filename': pr.get('filename', 'ocr_readable.txt'),
            'is_human_readable': True,
            'total_ocr_texts': pr.get('total_ocr_texts', 0),
            'corrected_texts': pr.get('corrected_texts', 0),
            'content_length': content_length,
            'save_time': pr.get('save_time'),
            'format': 'txt'
        }
        drawing.processing_result = json.dumps(pr, ensure_ascii=False)
        fixed += 1
    session.commit()
    print(f"已补全 {fixed} 条记录的S3 URL")
    session.close()

if __name__ == "__main__":
    fix_processing_result_s3_url() 