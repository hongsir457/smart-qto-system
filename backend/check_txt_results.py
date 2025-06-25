from app.database import get_db
from app.models.drawing import Drawing
import json

db_gen = get_db()
db = next(db_gen)

drawing = db.query(Drawing).first()

if drawing and drawing.processing_result:
    proc_result = json.loads(drawing.processing_result)
    txt_result = proc_result.get('human_readable_txt', {})
    
    print('📊 TXT格式结果信息:')
    print(f'  S3 URL: {txt_result.get("s3_url", "未找到")}')
    print(f'  S3 Key: {txt_result.get("s3_key", "未找到")}')
    print(f'  是否人类可读: {txt_result.get("is_human_readable", False)}')
    print(f'  纠正文本数: {txt_result.get("corrected_texts", 0)}')
    print(f'  内容长度: {txt_result.get("content_length", 0)}字符')
    print(f'  文件名: {txt_result.get("filename", "未知")}')
    print(f'  格式: {txt_result.get("format", "未知")}')
else:
    print('❌ 未找到图纸记录或processing_result为空') 