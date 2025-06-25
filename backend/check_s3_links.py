from app.database import get_db
from app.models.drawing import Drawing
import json

db_gen = get_db()
db = next(db_gen)

drawing = db.query(Drawing).first()

if drawing and drawing.processing_result:
    proc_result = json.loads(drawing.processing_result)
    real_readable = proc_result.get('real_readable_result', {})
    
    print('📊 数据库中的S3链接信息:')
    print(f'  S3 URL: {real_readable.get("s3_url", "未找到")}')
    print(f'  S3 Key: {real_readable.get("s3_key", "未找到")}')
    print(f'  是否真实数据: {real_readable.get("is_real_data", False)}')
    print(f'  总文本数: {real_readable.get("total_ocr_texts", 0)}')
    print(f'  保存时间: {real_readable.get("save_time", "未知")}')
else:
    print('❌ 未找到图纸记录或processing_result为空') 