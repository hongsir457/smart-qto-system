from app.database import get_db
from app.models.drawing import Drawing

session = next(get_db())
drawing = session.query(Drawing).filter(Drawing.id == 1).first()

print("=== 图纸1转换后的A→B→C验证 ===")
pr = drawing.processing_result
abc_keys = ['result_a_raw_ocr', 'result_b_corrected_json', 'result_c_human_readable']

for key in abc_keys:
    exists = key in pr
    if exists and isinstance(pr[key], dict) and 's3_url' in pr[key]:
        print(f"{key}: ✅ (S3: {pr[key]['s3_url']})")
    else:
        print(f"{key}: ❌")

# 检查兼容字段
if 'human_readable_txt' in pr:
    print(f"human_readable_txt: ✅ (S3: {pr['human_readable_txt']['s3_url']})")
else:
    print("human_readable_txt: ❌")

session.close() 